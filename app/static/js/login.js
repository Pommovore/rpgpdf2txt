// Lecture dynamique du préfixe de l'application
const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const errorDiv = document.getElementById('loginError');
    errorDiv.classList.add('d-none');

    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/auth/login`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            errorDiv.textContent = data.detail || 'Échec de la connexion';
            errorDiv.classList.remove('d-none');
        } else {
            localStorage.setItem('access_token', data.access_token);
            window.location.href = `${APP_PREFIX}/dashboard`;
        }
    } catch (err) {
        errorDiv.textContent = 'Erreur serveur. Veuillez réessayer plus tard.';
        errorDiv.classList.remove('d-none');
    }
});
