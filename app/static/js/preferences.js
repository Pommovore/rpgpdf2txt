// Lecture dynamique du préfixe de l'application
const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = `${APP_PREFIX}/login`;
}

async function loadUserProfile() {
    const tokenInput = document.getElementById('apiTokenInput');
    if (!tokenInput) return;

    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const user = await response.json();
            tokenInput.value = user.api_token || "Token non généré (contactez l'administrateur)";
        } else {
            tokenInput.value = `Erreur ${response.status} (Profil)`;
        }
    } catch (err) {
        tokenInput.value = "Erreur réseau/connexion";
    }
}

function copyApiToken() {
    const tokenInput = document.getElementById('apiTokenInput');
    if (!tokenInput || !tokenInput.value || tokenInput.value.startsWith("Token non")) return;

    tokenInput.select();
    tokenInput.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(tokenInput.value).catch(err => {
        console.error("Erreur copie", err);
    });

    const btn = document.getElementById('copyTokenBtn');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check2"></i>';
    btn.classList.add('btn-success');
    btn.classList.remove('btn-outline-secondary');

    setTimeout(() => {
        btn.innerHTML = originalHtml;
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
    }, 2000);
}

document.getElementById('changePasswordForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const currentPassword = document.getElementById('current_password').value;
    const newPassword = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const msgDiv = document.getElementById('passwordMsg');

    if (newPassword !== confirmPassword) {
        msgDiv.textContent = 'Les nouveaux mots de passe ne correspondent pas';
        msgDiv.className = 'alert alert-danger d-block';
        return;
    }

    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/auth/change-password`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (response.ok) {
            msgDiv.textContent = 'Mot de passe mis à jour avec succès';
            msgDiv.className = 'alert alert-success d-block';
            e.target.reset();
        } else {
            msgDiv.textContent = data.detail || 'Échec de la mise à jour';
            msgDiv.className = 'alert alert-danger d-block';
        }
    } catch (err) {
        msgDiv.textContent = 'Erreur serveur lors de la mise à jour';
        msgDiv.className = 'alert alert-danger d-block';
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadUserProfile();
});
