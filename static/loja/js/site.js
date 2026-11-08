document.addEventListener('DOMContentLoaded', function () {
    const themeStorageKey = 'mira_theme';
    const root = document.documentElement;
    const themeToggle = document.querySelector('[data-theme-toggle]');

    function setTheme(theme) {
        const isLight = theme === 'light';
        root.dataset.theme = theme;
        root.style.colorScheme = theme;
        document.querySelector('meta[name="theme-color"]')?.setAttribute('content', isLight ? '#eef3ec' : '#101813');

        if (!themeToggle) return;
        themeToggle.setAttribute('aria-checked', String(isLight));
        themeToggle.setAttribute('title', isLight ? 'Ativar modo escuro' : 'Ativar modo claro');
        const icon = themeToggle.querySelector('[data-theme-icon]');
        if (icon) icon.textContent = isLight ? '☾' : '☀';
    }

    setTheme(root.dataset.theme === 'light' ? 'light' : 'dark');

    themeToggle?.addEventListener('click', function () {
        const nextTheme = root.dataset.theme === 'light' ? 'dark' : 'light';
        try {
            localStorage.setItem(themeStorageKey, nextTheme);
        } catch (error) {
            // O controlo continua a funcionar quando o navegador bloqueia o armazenamento.
        }
        setTheme(nextTheme);
    });

    const firstGuideKey = 'mira_first_guide_seen';
    const seen = localStorage.getItem(firstGuideKey) === 'true';

    const modalEl = document.getElementById('firstGuideModal');
    if (!modalEl || seen || window.location.pathname !== '/' || !window.bootstrap) return;

    const modal = new bootstrap.Modal(modalEl);
    const steps = Array.from(document.querySelectorAll('[data-tour-step]'));
    const dots = Array.from(document.querySelectorAll('[data-step-dot]'));
    const backBtn = document.querySelector('[data-tour-back]');
    const nextBtn = document.querySelector('[data-tour-next]');
    const skipBtn = document.querySelector('[data-tour-skip]');
    const dynamicLayouts = Array.from(document.querySelectorAll('[data-tour-layout]'));
    let currentStep = 0;

    function renderStep(index) {
        steps.forEach((step, i) => {
            const active = i === index;
            step.classList.toggle('active', active);
            step.hidden = !active;
        });
        dynamicLayouts.forEach((layout) => {
            layout.dataset.tourLayout = String(index);
        });
        dots.forEach((dot, i) => {
            const active = i === index;
            dot.classList.toggle('active', active);
            dot.setAttribute('aria-current', active ? 'step' : 'false');
        });
        backBtn.disabled = index === 0;
        nextBtn.textContent = index === steps.length - 1 ? 'Finalizar' : 'Próximo';
    }

    function finishTour() {
        localStorage.setItem(firstGuideKey, 'true');
        modal.hide();
    }

    backBtn.addEventListener('click', function () {
        if (currentStep > 0) renderStep(--currentStep);
    });
    nextBtn.addEventListener('click', function () {
        if (currentStep < steps.length - 1) renderStep(++currentStep);
        else finishTour();
    });
    skipBtn.addEventListener('click', finishTour);
    modalEl.addEventListener('hidden.bs.modal', finishTour, {once: true});
    renderStep(currentStep);
    modal.show();
});
