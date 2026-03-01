// Lecture dynamique du préfixe de l'application
const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = `${APP_PREFIX}/login`;
}

// Intervalle de polling (null = inactif)
let pollingInterval = null;
const POLL_DELAY_MS = 5000;

function logout() {
    localStorage.removeItem('access_token');
    stopPolling();
    window.location.href = `${APP_PREFIX}/login`;
}

/**
 * Démarre le rafraîchissement automatique du tableau des demandes.
 */
function startPolling() {
    if (pollingInterval) return; // Déjà actif
    pollingInterval = setInterval(loadRequests, POLL_DELAY_MS);
    updatePollingIndicator(true);
}

/**
 * Arrête le rafraîchissement automatique.
 */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    updatePollingIndicator(false);
}

/**
 * Met à jour l'indicateur visuel de rafraîchissement automatique.
 */
function updatePollingIndicator(active) {
    const indicator = document.getElementById('pollingIndicator');
    if (indicator) {
        indicator.style.display = active ? 'inline' : 'none';
    }
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
            loadRequests();
            // Démarrer le polling automatique
            startPolling();
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

async function loadRequests() {
    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/user/requests`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            window.location.href = `${APP_PREFIX}/login`;
            return;
        }

        const requests = await response.json();
        const tbody = document.getElementById('requestsTableBody');
        tbody.innerHTML = '';

        if (requests.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3">Aucune demande d\'extraction trouvée</td></tr>';
            stopPolling();
            return;
        }

        // Vérifie s'il reste des extractions en cours
        const hasActiveJobs = requests.some(r => r.status === 'pending' || r.status === 'processing');

        requests.forEach(req => {
            const tr = document.createElement('tr');

            let statusBadge = '';
            let actionBtn = '';

            switch (req.status) {
                case 'success':
                    statusBadge = '<span class="badge bg-success">Terminé</span>';
                    actionBtn = `<a href="${APP_PREFIX}/api/v1/extract/${req.id}/download?token=${token}" target="_blank" class="btn btn-sm btn-outline-success">Télécharger .txt</a>`;
                    break;
                case 'pending':
                    statusBadge = '<span class="badge bg-warning text-dark">En attente</span>';
                    actionBtn = `<span class="text-muted small">Dans la file d\'attente</span>`;
                    break;
                case 'processing':
                    statusBadge = '<span class="badge bg-info text-dark"><span class="spinner-border spinner-border-sm me-1"></span>En cours</span>';
                    actionBtn = `<span class="text-muted small">Extraction...</span>`;
                    break;
                case 'error':
                    statusBadge = '<span class="badge bg-danger">Erreur</span>';
                    actionBtn = `<span class="text-danger small" title="${req.error_message || 'Erreur inconnue'}">Échec</span>`;
                    break;
            }

            const date = req.created_at ? new Date(req.created_at).toLocaleString() : '-';

            tr.innerHTML = `
                <td>${req.id}</td>
                <td><strong>${req.id_texte}</strong></td>
                <td>${statusBadge}</td>
                <td class="small text-muted">${date}</td>
                <td>${actionBtn}</td>
            `;
            tbody.appendChild(tr);
        });

        // Arrêter le polling si plus rien n'est en cours
        if (!hasActiveJobs) {
            stopPolling();
        }
    } catch (err) {
        console.error('Échec du chargement des demandes', err);
    }
}

async function loadUserProfile() {
    const tokenInput = document.getElementById('apiTokenInput');
    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const user = await response.json();
            if (tokenInput) {
                tokenInput.value = user.api_token || "Token non généré (contactez l'administrateur)";
            }
        } else {
            console.error('Erreur profil:', response.status);
            if (tokenInput) {
                tokenInput.value = `Erreur ${response.status} (Profil)`;
            }
        }
    } catch (err) {
        console.error('Erreur lors du chargement du profil utilisateur:', err);
        if (tokenInput) {
            tokenInput.value = "Erreur de connexion (Profil)";
        }
    }
}

function copyApiToken() {
    const tokenInput = document.getElementById('apiTokenInput');
    if (!tokenInput || !tokenInput.value || tokenInput.value.startsWith("Token non")) return;

    tokenInput.select();
    tokenInput.setSelectionRange(0, 99999); // Pour mobiles
    document.execCommand("copy");

    // Feedback visuel
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

document.addEventListener('DOMContentLoaded', () => {
    loadRequests();
    loadUserProfile();
});

