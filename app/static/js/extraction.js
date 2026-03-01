// Lecture dynamique du préfixe de l'application
const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = `${APP_PREFIX}/login`;
}

document.getElementById('extractForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const msgDiv = document.getElementById('extractMsg');
    const btn = document.getElementById('submitBtn');

    if (!formData.has('ia_validate')) {
        formData.append('ia_validate', 'false');
    }

    msgDiv.classList.add('d-none');
    msgDiv.classList.remove('alert-success', 'alert-danger');
    btn.disabled = true;
    btn.textContent = 'Envoi...';

    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/extract`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            msgDiv.textContent = 'Extraction démarrée (ID: ' + data.request_id + ')';
            msgDiv.classList.add('alert-success', 'd-block');
            form.reset();
            // Rediriger vers l'historique après un court délai pour voir le succès
            setTimeout(() => {
                window.location.href = `${APP_PREFIX}/history`;
            }, 2000);
        } else {
            msgDiv.textContent = data.detail || 'Échec du démarrage de l\'extraction';
            msgDiv.classList.add('alert-danger', 'd-block');
        }
    } catch (err) {
        msgDiv.textContent = 'Erreur serveur lors de l\'envoi';
        msgDiv.classList.add('alert-danger', 'd-block');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Démarrer l\'extraction';
    }
});
