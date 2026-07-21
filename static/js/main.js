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
