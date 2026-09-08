/* ============================================================
   SOVEREIGN — Theme Toggle
   theme.js — light/dark mode switch, persisted
   ============================================================ */

(function () {
    const root = document.documentElement;
    const saved = localStorage.getItem('sovereign-theme');
    if (saved) root.setAttribute('data-theme', saved);

    document.addEventListener('DOMContentLoaded', () => {
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;

        const sunIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
        const moonIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;

        btn.innerHTML = root.getAttribute('data-theme') === 'light' ? sunIcon : moonIcon;

        btn.addEventListener('click', () => {
            const next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            root.setAttribute('data-theme', next);
            localStorage.setItem('sovereign-theme', next);
            btn.innerHTML = next === 'light' ? sunIcon : moonIcon;

            if (window.Motion) {
                window.Motion.animate(document.body, { opacity: [0.4, 1] }, { duration: 0.3, easing: 'ease-out' });
            }
        });
    });
})();