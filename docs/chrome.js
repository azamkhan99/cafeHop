(function () {
    'use strict';

    function safeHttpUrl(url) {
        var s = String(url || '').trim();
        if (!s) return '';
        var low = s.slice(0, 8).toLowerCase();
        if (low.indexOf('https://') === 0 || low.indexOf('http://') === 0) return s;
        return '';
    }

    function cafeApiUrl() {
        var C = window.CafeHopConfig || {};
        return String(C.cafeUrl || '').replace(/\/$/, '');
    }

    function setPasteStatus(msg, isError) {
        ensureSheet();
        var el = sheetEl.querySelector('#watchlist-paste-status');
        if (!el) return;
        if (!msg) {
            el.hidden = true;
            el.textContent = '';
            return;
        }
        el.hidden = false;
        el.textContent = msg;
        el.classList.toggle('is-error', Boolean(isError));
    }

    var watchlistCache = [];

    function ingestMapsShare(raw, opts) {
        var quiet = Boolean(opts && opts.quiet);
        var text = String(raw || '').trim();
        if (!text) {
            if (!quiet) setPasteStatus('Paste a Maps link first.', true);
            return Promise.resolve(false);
        }
        if (!quiet) setPasteStatus('Looking up that place…');
        var api = cafeApiUrl();
        if (!api) {
            if (!quiet) setPasteStatus('Cafe API is not configured', true);
            return Promise.resolve(false);
        }
        return fetch(api + '/v1/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        }).then(function (res) {
            return res.json().then(function (body) {
                if (!res.ok) throw new Error(body.error || ('Add failed (' + res.status + ')'));
                return body;
            });
        }).then(function () {
            return refreshWatchlist();
        }).then(function () {
            if (!quiet) setPasteStatus('Added');
            renderSheetList();
            window.dispatchEvent(new CustomEvent('cafehop-watchlist-changed'));
            return true;
        }).catch(function (err) {
            if (!quiet) setPasteStatus(err && err.message ? err.message : 'Could not read that link.', true);
            return false;
        });
    }

    function consumeShareQuery() {
        try {
            var params = new URLSearchParams(location.search);
            var blob = [params.get('url'), params.get('text'), params.get('title'), params.get('gmaps')]
                .filter(Boolean)
                .join(' ');
            if (!/maps\.app\.goo\.gl|google\.com\/maps|maps\.google\.com/i.test(blob)) return;
            openWatchlistSheet();
            ingestMapsShare(blob).then(function (ok) {
                if (!ok) return;
                if (history.replaceState) {
                    history.replaceState({}, '', location.pathname);
                }
            });
        } catch (e) { /* ignore */ }
    }

    function getById(id) {
        return watchlistCache.filter(function (x) { return x.id === id; })[0] || null;
    }

    function loadList() {
        return watchlistCache.slice();
    }

    function refreshWatchlist() {
        var api = cafeApiUrl();
        if (!api) {
            watchlistCache = [];
            return Promise.resolve(watchlistCache);
        }
        return fetch(api + '/v1/watchlist').then(function (res) {
            return res.json().then(function (body) {
                if (!res.ok) throw new Error(body.error || ('Watchlist failed (' + res.status + ')'));
                watchlistCache = Array.isArray(body.watchlist) ? body.watchlist : [];
                return watchlistCache;
            });
        }).catch(function () {
            watchlistCache = [];
            return watchlistCache;
        });
    }

    function removeById(id) {
        var api = cafeApiUrl();
        if (!api || !id) return Promise.resolve();
        return fetch(api + '/v1/watchlist/' + encodeURIComponent(id), { method: 'DELETE' }).then(function () {
            return refreshWatchlist();
        });
    }

    var sheetEl = null;

    function ensureSheet() {
        if (sheetEl) return sheetEl;
        sheetEl = document.createElement('div');
        sheetEl.id = 'watchlist-sheet';
        sheetEl.className = 'watchlist-sheet';
        sheetEl.setAttribute('aria-hidden', 'true');
        sheetEl.innerHTML =
            '<div class="watchlist-sheet-backdrop" data-watchlist-close></div>' +
            '<div class="watchlist-sheet-panel" role="dialog" aria-label="Watchlist">' +
            '<div class="watchlist-sheet-handle"></div>' +
            '<div class="watchlist-sheet-title-row">' +
            '<span class="watchlist-sheet-title">Watchlist</span>' +
            '<button type="button" class="watchlist-sheet-close" data-watchlist-close aria-label="Close">×</button>' +
            '</div>' +
            '<form class="watchlist-paste" id="watchlist-paste-form">' +
            '<input type="url" id="watchlist-paste-input" class="watchlist-paste-input" ' +
            'placeholder="Paste a Google Maps link" autocomplete="off" enterkeyhint="done" />' +
            '<button type="submit" class="watchlist-paste-btn">Add</button>' +
            '</form>' +
            '<p class="watchlist-paste-status" id="watchlist-paste-status" hidden></p>' +
            '<div class="watchlist-sheet-list" id="watchlist-sheet-list"></div>' +
            '</div>';

        document.body.appendChild(sheetEl);

        sheetEl.addEventListener('click', function (e) {
            if (e.target && e.target.getAttribute('data-watchlist-close') != null) {
                closeWatchlistSheet();
            }
        });

        var pasteForm = sheetEl.querySelector('#watchlist-paste-form');
        if (pasteForm) {
            pasteForm.addEventListener('submit', function (e) {
                e.preventDefault();
                var input = sheetEl.querySelector('#watchlist-paste-input');
                var raw = input ? String(input.value || '').trim() : '';
                ingestMapsShare(raw).then(function (ok) {
                    if (ok && input) input.value = '';
                });
            });
        }

        return sheetEl;
    }

    function escapeHtml(text) {
        if (text == null || text === '') return '';
        var div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    function renderSheetList() {
        ensureSheet();
        var listEl = sheetEl.querySelector('#watchlist-sheet-list');
        if (!listEl) return;

        var items = loadList();
        if (items.length === 0) {
            listEl.innerHTML = '';
            return;
        }

        listEl.innerHTML = items.map(function (it) {
            var thumb = safeHttpUrl(it.thumbUrl);
            var sub = (it.neighborhood || '').trim();
            var pending = it.source === 'gmaps' || it.pending;
            var mapsHref = safeHttpUrl(it.mapsUrl);
            if (!mapsHref && it.lat != null && it.lng != null) {
                mapsHref = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(it.lat + ',' + it.lng);
            }
            var nameHtml = mapsHref
                ? '<a class="watchlist-row-name-link" href="' + escapeHtml(mapsHref) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(it.name) + '</a>'
                : escapeHtml(it.name);
            var addHref = 'add.html?watchlist=' + encodeURIComponent(it.id);
            var pendingMark = pending
                ? '<span class="watchlist-pending-badge" title="Watchlist">☆</span>'
                : '';
            var addBtn = pending
                ? '<a class="watchlist-row-log" href="' + addHref + '">Log café</a>'
                : '';
            return (
                '<div class="watchlist-row' + (pending ? ' is-pending' : '') + '" data-watchlist-id="' + escapeHtml(it.id) + '">' +
                (thumb
                    ? '<img class="watchlist-row-thumb" src="' + escapeHtml(thumb) + '" alt="" loading="lazy" referrerpolicy="no-referrer" />'
                    : '<div class="watchlist-row-thumb watchlist-row-thumb--empty" aria-hidden="true">☆</div>') +
                '<div class="watchlist-row-meta">' +
                '<div class="watchlist-row-name">' + pendingMark + nameHtml + '</div>' +
                (sub ? '<div class="watchlist-row-sub">' + escapeHtml(sub) + '</div>' : '') +
                addBtn +
                '</div>' +
                '<button type="button" class="watchlist-row-remove" data-watchlist-remove="' + escapeHtml(it.id) + '" aria-label="Remove">×</button>' +
                '</div>'
            );
        }).join('');

        listEl.querySelectorAll('[data-watchlist-remove]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-watchlist-remove');
                if (!id) return;
                removeById(id).then(function () {
                    renderSheetList();
                    window.dispatchEvent(new CustomEvent('cafehop-watchlist-changed'));
                });
            });
        });
    }

    function openWatchlistSheet() {
        ensureSheet();
        sheetEl.classList.add('is-open');
        sheetEl.setAttribute('aria-hidden', 'false');
        refreshWatchlist().then(function () {
            renderSheetList();
        });
    }

    function closeWatchlistSheet() {
        if (!sheetEl) return;
        sheetEl.classList.remove('is-open');
        sheetEl.setAttribute('aria-hidden', 'true');
    }

    var ICON_GALLERY =
        '<svg class="chrome-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<rect x="3.5" y="3.5" width="6.5" height="6.5" rx="1.25"/>' +
        '<rect x="14" y="3.5" width="6.5" height="6.5" rx="1.25"/>' +
        '<rect x="3.5" y="14" width="6.5" height="6.5" rx="1.25"/>' +
        '<rect x="14" y="14" width="6.5" height="6.5" rx="1.25"/>' +
        '</svg>';

    var ICON_WATCHLIST =
        '<svg class="chrome-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M6 2h12a1 1 0 011 1v19l-7-4-7 4V3a1 1 0 011-1z"/>' +
        '</svg>';

    var ICON_MAP =
        '<svg class="chrome-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M12 21s7-4.5 7-11a7 7 0 10-14 0c0 6.5 7 11 7 11z"/>' +
        '<circle cx="12" cy="10" r="2" fill="currentColor" stroke="none"/>' +
        '</svg>';

    /** One canonical bottom nav for index / add / map (markup + active state from data-chrome-page). */
    function ensureChromeFooter() {
        if (!document.body.classList.contains('has-chrome')) return;
        var old = document.querySelector('.chrome-footer');
        if (old) old.remove();

        var page = document.body.getAttribute('data-chrome-page') || '';
        var galActive = page === 'gallery';
        var fabActive = page === 'add';
        var mapActive = page === 'map';

        var galCls = 'chrome-nav-a chrome-nav-gallery' + (galActive ? ' is-active' : '');
        var galExtra = galActive ? ' aria-current="page"' : '';
        var fabCls = 'chrome-fab-add' + (fabActive ? ' is-active' : '');
        var fabExtra = fabActive ? ' aria-current="page"' : '';
        var mapCls = 'chrome-nav-a chrome-nav-map' + (mapActive ? ' is-active' : '');
        var mapExtra = mapActive ? ' aria-current="page"' : '';

        var html =
            '<div class="chrome-footer-track">' +
            '<div class="chrome-footer-side chrome-footer-side--leading">' +
            '<a href="index.html" class="' + galCls + '" aria-label="Gallery"' + galExtra + '>' + ICON_GALLERY + '</a>' +
            '</div>' +
            '<div class="chrome-footer-center">' +
            '<a href="add.html" class="' + fabCls + '" aria-label="Add café"' + fabExtra + '>+</a>' +
            '</div>' +
            '<div class="chrome-footer-side chrome-footer-side--trailing">' +
            '<button type="button" class="chrome-footer-btn chrome-nav-watchlist" data-watchlist-open aria-label="Watchlist">' +
            ICON_WATCHLIST +
            '</button>' +
            '<a href="map.html" class="' + mapCls + '" aria-label="Map"' + mapExtra + '>' + ICON_MAP + '</a>' +
            '</div>' +
            '</div>';

        var footer = document.createElement('footer');
        footer.className = 'chrome-footer';
        footer.innerHTML = html;
        document.body.appendChild(footer);
    }

    document.addEventListener('DOMContentLoaded', function () {
        ensureChromeFooter();
        ensureSheet();
        document.querySelectorAll('[data-watchlist-open]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                openWatchlistSheet();
            });
        });
        consumeShareQuery();
        refreshWatchlist();
    });

    window.CafeHopWatchlist = {
        loadList: loadList,
        getById: getById,
        refresh: refreshWatchlist,
        removeById: removeById,
        ingestMapsShare: ingestMapsShare,
        openWatchlistSheet: openWatchlistSheet,
        closeWatchlistSheet: closeWatchlistSheet
    };
})();
