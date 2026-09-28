#!/usr/bin/env python3
"""The visit counter: one number per page, from Abacus.

These pages are static files on GitHub Pages, so a count has to come from
somewhere else. GitHub itself cannot supply it -- the repository traffic API
counts people browsing the repo on github.com, not visitors to the Pages site,
it needs a write-scoped token that cannot go in a public page, and it only
keeps fourteen days. Verified 2026-09-27: every project repo read zero views
with no popular paths while its Pages site was live, and the only path GitHub
had recorded anywhere was "/TNRiley/quick-projects" ("Overview").

So: https://abacus.jasoncameron.dev, a bare hit counter with no account and no
dashboard. One namespace, one key per page.

    GET /hit/<ns>/<key>   increment, create if absent -> {"value": 12}
    GET /get/<ns>/<key>   read without incrementing   -> {"value": 12}
                          404 {"error":"Key not found"} if never hit

Three things about it shape the code below.

**The namespace is public**, visible to anyone who reads the page source, and
the service is shared by everybody using it. So the namespace carries a random
suffix: not to stop someone inflating the numbers (nothing can, on a service
with no accounts) but so it cannot collide with another person's "quick-projects".
Treat these numbers as interesting, not as evidence.

**30 requests per IP per 10 seconds**, and the shelf already has more cards
than that. The catalog therefore reads card counts lazily as cards scroll into
view, one at a time with a gap, and never reads a card twice in a session.
The gap is 500ms rather than something snappier because the ceiling works out
at three requests a second sustained: a 220ms gap was tried first and is over
it. Hitting the limit is not hypothetical, it happened while seeding the test
counters from a shell loop. A 429 is not ok, so it reads as no number at all,
which on a page that shows nothing by default is invisible.

**A free service with no uptime promise will eventually stop answering.** Every
number here is injected by JavaScript on success and does not exist in the HTML
at all. When Abacus is slow, blocked by a tracker blocker, rate-limiting, or
gone for good, no element is created and the page looks exactly as it did
before any of this was added. Nothing renders a zero, a dash or a spinner.

Keys must match ^[A-Za-z0-9_.-]{3,64}$, which every project slug already does.
An untouched key expires after six months, refreshed on every access, so a
project nobody opens for half a year loses its count.
"""

NAMESPACE = "tnriley-shelf-e76198"
API = "https://abacus.jasoncameron.dev"
CATALOG_KEY = "catalog"

# Only a page served from the live site increments anything. Opening a built
# file locally to check it -- which happens a lot, and used to happen once per
# tweak -- reads the count instead, so previewing never inflates it.
_LIVE = r'/\.github\.io$/i.test(location.hostname)'


def project_snippet(slug):
    """The counter for one project page, injected into the catalog breadcrumb bar.

    Appends "1,284 visits" to the right-hand end of the bar, or appends nothing.
    """
    return """<script>
(function(){
  var nav = document.querySelector(".qp-crumb"); if (!nav) return;
  var live = %(live)s;
  fetch("%(api)s/" + (live ? "hit" : "get") + "/%(ns)s/%(key)s", {cache: "no-store"})
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(d){
      if (!d || typeof d.value !== "number") return;
      var s = document.createElement("span");
      s.className = "qp-visits";
      s.textContent = d.value.toLocaleString("en-US") + (d.value === 1 ? " visit" : " visits");
      nav.appendChild(s);
    })
    .catch(function(){});
})();
</script>""" % {"api": API, "ns": NAMESPACE, "key": slug, "live": _LIVE}


def catalog_script():
    """The counter for the catalog page: its own visits, plus one per card."""
    return """<script>
(function(){
  "use strict";
  var API = "%(api)s", NS = "%(ns)s";
  var live = %(live)s;
  var fmt = function(n){ return n.toLocaleString("en-US"); };
  /* The 6s timeout matters more than it looks: the card reads run through a
     single queue, so one request left hanging would stall every card behind it
     for good. Aborting turns that into an ordinary miss, which renders nothing. */
  var read = function(url){
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = ctl && setTimeout(function(){ ctl.abort(); }, 6000);
    return fetch(url, {cache: "no-store", signal: ctl ? ctl.signal : undefined})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){ return (d && typeof d.value === "number") ? d.value : null; })
      .catch(function(){ return null; })
      .then(function(v){ if (timer) clearTimeout(timer); return v; });
  };

  /* this page's own visits, next to the masthead label */
  var lbl = document.getElementById("mastLbl");
  if (lbl) read(API + "/" + (live ? "hit" : "get") + "/" + NS + "/%(catkey)s").then(function(v){
    if (v === null) return;
    var s = document.createElement("span");
    s.className = "visits";
    s.textContent = fmt(v) + (v === 1 ? " visit" : " visits");
    lbl.appendChild(document.createTextNode(" \u00b7 "));
    lbl.appendChild(s);
  });

  /* One count per card, read (never incremented) as the card comes into view.
     Abacus allows 30 requests per IP per 10 seconds and the shelf is bigger
     than that, so these go one at a time with a gap rather than all at once. */
  var queue = [], busy = false;
  function pump(){
    if (busy || !queue.length) return;
    busy = true;
    var card = queue.shift();
    read(API + "/get/" + NS + "/" + card.getAttribute("data-visits")).then(function(v){
      if (v !== null) {
        var dl = card.querySelector(".meta dl");
        if (dl) {
          var row = document.createElement("div");
          row.innerHTML = "<dt>Visits</dt><dd></dd>";
          row.lastChild.textContent = fmt(v);
          dl.appendChild(row);
        }
      }
      busy = false;
      setTimeout(pump, 500);   /* 2/s; the ceiling is 3/s sustained */
    });
  }

  var cards = [].slice.call(document.querySelectorAll(".card[data-visits]"));
  if (window.IntersectionObserver) {
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (!e.isIntersecting) return;
        io.unobserve(e.target);      /* once per session, never re-read on scroll back */
        queue.push(e.target); pump();
      });
    }, {rootMargin: "250px"});
    cards.forEach(function(c){ io.observe(c); });
  } else {
    cards.forEach(function(c){ queue.push(c); });
    pump();
  }
})();
</script>""" % {"api": API, "ns": NAMESPACE, "catkey": CATALOG_KEY, "live": _LIVE}
