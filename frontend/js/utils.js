(function (root) {
    'use strict';

    const MAP = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    };

    function escapeHTML(value) {
        return String(value ?? '').replace(/[&<>"']/g, ch => MAP[ch]);
    }

    root.escapeHTML = escapeHTML;
})(typeof window !== 'undefined' ? window : globalThis);
