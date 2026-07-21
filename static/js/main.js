function validatePassword() {
    const pw = document.getElementById('password').value;
    const cf = document.getElementById('password_confirm').value;
    const checks = {
        'req-len': pw.length >= 8,
        'req-up': /[A-Z]/.test(pw),
        'req-low': /[a-z]/.test(pw),
        'req-dig': /\d/.test(pw),
        'req-sym': /[^A-Za-z0-9]/.test(pw),
    };
    for (const id in checks) {
        const el = document.getElementById(id);
        el.className = 'pw-req' + (checks[id] ? ' pw-ok' : ' pw-ko');
        el.textContent = (checks[id] ? '\u2713' : '\u2717') + el.textContent.slice(1);
    }
    const match = document.getElementById('pw-match');
    if (cf.length === 0) {
        match.textContent = '';
    } else if (pw === cf) {
        match.textContent = '\u2713 Coinciden';
        match.className = 'nexus-hint nexus-pw-match pw-ok';
    } else {
        match.textContent = '\u2717 No coinciden';
        match.className = 'nexus-hint nexus-pw-match';
    }
}
document.addEventListener('htmx:afterSwap', function () {
    document.querySelectorAll('.markdown-body').forEach(function (el) {
        if (!el.dataset.rendered) {
            el.innerHTML = DOMPurify.sanitize(marked.parse(el.textContent));
            el.dataset.rendered = 'true';
        }
    });
});

document.addEventListener('htmx:afterSwap', function () {
    if (typeof DOMPurify === 'undefined') return;
    document.querySelectorAll('a[href]').forEach(function (el) {
        if (!el.rel) el.rel = 'noopener noreferrer';
    });
});

document.addEventListener('click', function (evt) {
    const btn = evt.target.closest('.nexus-btn-copy');
    if (!btn) return;
    const answer = btn.closest('.nexus-result-answer');
    if (!answer) return;
    const body = answer.querySelector('.markdown-body');
    if (!body) return;
    navigator.clipboard.writeText(body.textContent).then(function () {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'nexus-toast nexus-toast-success';
        toast.textContent = 'Copiado al portapapeles';
        container.appendChild(toast);
        setTimeout(function () { toast.remove(); }, 4000);
    });
});

document.addEventListener('input', function (evt) {
    if (!evt.target.matches('.nexus-doc-filter')) return;
    const filter = evt.target.value.toLowerCase();
    const select = document.getElementById('document_ids');
    if (!select) return;
    for (let i = 0; i < select.options.length; i++) {
        const opt = select.options[i];
        opt.style.display = opt.text.toLowerCase().includes(filter) ? '' : 'none';
    }
});

document.addEventListener('click', function (evt) {
    const pill = evt.target.closest('.nexus-pill');
    if (!pill) return;
    const pills = pill.closest('.nexus-pills');
    if (!pills) return;
    pills.querySelectorAll('.nexus-pill').forEach(function (p) {
        p.classList.remove('active');
    });
    pill.classList.add('active');
});

(function () {
    const pills = document.querySelector('.nexus-pills');
    if (!pills) return;
    const consultar = pills.querySelector('[hx-get="/web/query"]');
    if (consultar) consultar.classList.add('active');
})();
