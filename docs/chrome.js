(function () {
    'use strict';

    var STORAGE_KEY = 'cafeHopWatchlistV1';

    function safeHttpUrl(url) {
        var s = String(url || '').trim();
        if (!s) return '';
        var low = s.slice(0, 8).toLowerCase();
        if (low.indexOf('https://') === 0 || low.indexOf('http://') === 0) return s;
        return '';
    }

    function cafeId(cafe) {
        var k = cafe && cafe.key != null ? String(cafe.key).trim() : '';
        if (k) return k;
        var name = (cafe && cafe.name) ? String(cafe.name).trim() : '';
        var img = safeHttpUrl(cafe && (cafe.imageUrl || cafe.thumbnailUrl)) || '';
        return 'n:' + name + '|u:' + img.slice(-120);
    }

    function entryFromCafe(cafe) {
        var thumb = safeHttpUrl(cafe.thumbnailUrl || cafe.imageUrl) || '';
        return {
            id: cafeId(cafe),
            name: (cafe.name || '').trim() || 'Café',
            thumbUrl: thumb,
            neighborhood: cafe.neighborhood || '',
            lat: cafe.latitude != null ? Number(cafe.latitude) : null,
            lng: cafe.longitude != null ? Number(cafe.longitude) : null
        };
    }

    function loadList() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return [];
            var arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr : [];
        } catch (e) {
            return [];
        }
    }

    function saveList(arr) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
        } catch (e) { /* ignore quota */ }
    }

    function addEntry(entry) {
        var list = loadList().filter(function (x) { return x.id !== entry.id; });
        list.unshift(entry);
        saveList(list);
    }

    function removeById(id) {
        saveList(loadList().filter(function (x) { return x.id !== id; }));
    }

    function toggleCafe(cafe) {
        var id = cafeId(cafe);
        var list = loadList();
        var exists = list.some(function (x) { return x.id === id; });
        if (exists) {
            removeById(id);
            return false;
        }
        addEntry(entryFromCafe(cafe));
        return true;
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
            '<label class="watchlist-only-row" id="watchlist-only-wrap" style="display:none">' +
            '<input type="checkbox" id="watchlist-only-gallery" />' +
            '<span>Show watchlist only in gallery</span>' +
            '</label>' +
            '<div class="watchlist-sheet-list" id="watchlist-sheet-list"></div>' +
            '</div>';

        document.body.appendChild(sheetEl);

        sheetEl.addEventListener('click', function (e) {
            if (e.target && e.target.getAttribute('data-watchlist-close') != null) {
                closeWatchlistSheet();
            }
        });

        var onlyWrap = sheetEl.querySelector('#watchlist-only-wrap');
        var onlyCb = sheetEl.querySelector('#watchlist-only-gallery');
        if (document.body.getAttribute('data-chrome-page') === 'gallery' && onlyWrap && onlyCb) {
            onlyWrap.style.display = 'flex';
            onlyCb.addEventListener('change', function () {
                window.dispatchEvent(new CustomEvent('cafehop-watchlist-only', { detail: { only: onlyCb.checked } }));
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
            listEl.innerHTML = '<p class="watchlist-sheet-empty">No places on your watchlist yet.</p>';
            return;
        }

        listEl.innerHTML = items.map(function (it) {
            var thumb = safeHttpUrl(it.thumbUrl);
            var sub = (it.neighborhood || '').trim();
            var maps = it.lat != null && it.lng != null && !isNaN(it.lat) && !isNaN(it.lng)
                ? 'https://www.google.com/maps?q=' + encodeURIComponent(it.lat + ',' + it.lng)
                : '';
            var mapsBtn = maps
                ? '<a class="watchlist-row-sub" href="' + escapeHtml(maps) + '" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:4px">Open in Maps</a>'
                : '';
            return (
                '<div class="watchlist-row" data-watchlist-id="' + escapeHtml(it.id) + '">' +
                (thumb ? '<img class="watchlist-row-thumb" src="' + escapeHtml(thumb) + '" alt="" loading="lazy" />' : '<div class="watchlist-row-thumb"></div>') +
                '<div class="watchlist-row-meta">' +
                '<div class="watchlist-row-name">' + escapeHtml(it.name) + '</div>' +
                (sub ? '<div class="watchlist-row-sub">' + escapeHtml(sub) + '</div>' : '') +
                mapsBtn +
                '</div>' +
                '<button type="button" class="watchlist-row-remove" data-watchlist-remove="' + escapeHtml(it.id) + '" aria-label="Remove">×</button>' +
                '</div>'
            );
        }).join('');

        listEl.querySelectorAll('[data-watchlist-remove]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-watchlist-remove');
                if (id) removeById(id);
                renderSheetList();
                window.dispatchEvent(new CustomEvent('cafehop-watchlist-changed'));
            });
        });
    }

    function openWatchlistSheet() {
        ensureSheet();
        renderSheetList();
        var onlyCb = sheetEl.querySelector('#watchlist-only-gallery');
        if (onlyCb && typeof window.__cafeHopWatchlistOnly === 'boolean') {
            onlyCb.checked = window.__cafeHopWatchlistOnly;
        }
        sheetEl.classList.add('is-open');
        sheetEl.setAttribute('aria-hidden', 'false');
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
    });

    window.CafeHopWatchlist = {
        cafeId: cafeId,
        loadList: loadList,
        toggleCafe: toggleCafe,
        removeById: removeById,
        openWatchlistSheet: openWatchlistSheet,
        closeWatchlistSheet: closeWatchlistSheet
    };
})();
