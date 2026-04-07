document.addEventListener('DOMContentLoaded', () => {
    const menu = document.getElementById('auth-account-menu');

    // Auth menu toggle
    document.addEventListener('click', (e) => {
        const toggle = e.target.closest('#auth-toggle-btn');
        if (!menu) return;

        if (toggle) {
            e.stopPropagation();
            menu.classList.toggle('open');
            return;
        }

        if (!e.target.closest('#auth-account-menu')) {
            menu.classList.remove('open');
        }
    });

    // Bottom taskbar active indicator
    const taskbar = document.querySelector('.bottom-taskbar');
    if (!taskbar) return;

    const indicator = taskbar.querySelector('.nav-indicator');
    const active = taskbar.querySelector('.taskbar-nav-link.active');
    if (!indicator || !active) return;

    const updateIndicator = () => {
        const taskbarRect = taskbar.getBoundingClientRect();
        const activeRect = active.getBoundingClientRect();

        indicator.style.left = `${activeRect.left - taskbarRect.left}px`;
        indicator.style.width = `${activeRect.width}px`;
        indicator.style.opacity = '0.35';
    };

    updateIndicator();
    window.addEventListener('resize', updateIndicator);
});
