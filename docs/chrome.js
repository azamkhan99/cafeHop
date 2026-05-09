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

    document.addEventListener('DOMContentLoaded', function () {
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
