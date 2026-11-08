document.addEventListener('DOMContentLoaded', function () {
    const marketHome = document.querySelector('.market-home');
    if (!marketHome) return;

    const root = document.documentElement;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const revealItems = Array.from(document.querySelectorAll('.home-reveal'));

    root.classList.add('experience-enhanced');

    if (reducedMotion || !('IntersectionObserver' in window)) {
        revealItems.forEach(function (item) {
            item.classList.add('is-visible');
        });
        root.classList.add('experience-ready');
        return;
    }

    const observer = new IntersectionObserver(function (entries, activeObserver) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            activeObserver.unobserve(entry.target);
        });
    }, { rootMargin: '0px 0px -8%', threshold: 0.12 });

    revealItems.forEach(function (item) {
        observer.observe(item);
    });

    window.requestAnimationFrame(function () {
        root.classList.add('experience-ready');
    });
});
