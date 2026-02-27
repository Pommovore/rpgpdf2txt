// Lecture dynamique du préfixe de l'application
const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = `${APP_PREFIX}/login`;
}

function logout() {
    localStorage.removeItem('access_token');
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
            loadRequests();
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
            return;
        }

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
                    statusBadge = '<span class="badge bg-info text-dark">En cours</span>';
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
    } catch (err) {
        console.error('Échec du chargement des demandes', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadRequests();
});
