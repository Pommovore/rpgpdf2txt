// Lecture dynamique du préfixe de l'application
const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = `${APP_PREFIX}/login`;
}

// Intervalle de polling (null = inactif)
let pollingInterval = null;
const POLL_DELAY_MS = 5000;

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    updatePollingIndicator(false);
}

function updatePollingIndicator(active) {
    const indicator = document.getElementById('pollingIndicator');
    if (indicator) {
        indicator.style.display = active ? 'inline' : 'none';
    }
}

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

        const hasActiveJobs = requests.some(r => r.status === 'pending' || r.status === 'processing');

        requests.forEach((req, index) => {
            const tr = document.createElement('tr');
            let statusBadge = '';
            let actionBtn = '';
            let idColumnHtml = req.id; // Par défaut, on affiche juste l'ID métier

            switch (req.status) {
                case 'success':
                    statusBadge = '<span class="badge bg-success">Terminé</span>';
                    actionBtn = `<a href="${APP_PREFIX}/api/v1/extract/${req.id}/download?token=${token}" target="_blank" class="btn btn-sm btn-outline-success"><i class="bi bi-download"></i> .txt</a>`;
                    break;
                case 'success_cached':
                    statusBadge = '<span class="badge bg-secondary">Caché</span>';
                    actionBtn = `<a href="${APP_PREFIX}/api/v1/extract/${req.id}/download?token=${token}" target="_blank" class="btn btn-sm btn-outline-secondary"><i class="bi bi-download"></i> .txt</a>`;
                    if (req.file_hash) {
                        idColumnHtml = `
                            <span class="badge border border-secondary text-secondary" style="cursor: help;"
                                  data-bs-toggle="tooltip" 
                                  data-bs-placement="top" 
                                  title="${req.file_hash}">
                                <i class="bi bi-hdd-network"></i> Caché
                            </span>
                         `;
                    }
                    break;
                case 'pending':
                    statusBadge = '<span class="badge bg-warning text-dark">En attente</span>';
                    actionBtn = `<span class="text-muted small">En attente</span>`;
                    if (req.queue_position !== undefined && req.queue_position !== null) {
                        idColumnHtml = `<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split"></i> Attente : ${req.queue_position + 1}</span>`;
                    }
                    break;
                case 'processing':
                    statusBadge = '<span class="badge bg-info text-dark"><span class="spinner-border spinner-border-sm me-1"></span>En cours</span>';
                    actionBtn = `<span class="text-muted small">Extraction...</span>`;
                    if (req.queue_position !== undefined && req.queue_position !== null) {
                        idColumnHtml = `<span class="badge bg-info text-dark"><i class="bi bi-gear-wide-connected"></i> En cours (0)</span>`;
                    }
                    break;
                case 'error':
                    statusBadge = '<span class="badge bg-danger">Erreur</span>';
                    actionBtn = `<span class="text-danger small" title="${req.error_message || 'Erreur inconnue'}">Échec</span>`;
                    break;
            }

            const date = req.created_at ? new Date(req.created_at).toLocaleString() : '-';

            tr.innerHTML = `
                <td>${idColumnHtml}</td>
                <td><strong>${req.id_texte}</strong></td>
                <td>${statusBadge}</td>
                <td class="small text-muted">${date}</td>
                <td>${actionBtn}</td>
            `;
            tbody.appendChild(tr);
        });

        // Initialisation des tooltips fraîchement ajoutés au DOM
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('#requestsTableBody [data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        if (hasActiveJobs && !pollingInterval) {
            pollingInterval = setInterval(loadRequests, POLL_DELAY_MS);
            updatePollingIndicator(true);
        } else if (!hasActiveJobs && pollingInterval) {
            stopPolling();
        }
    } catch (err) {
        console.error('Échec du chargement des demandes', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadRequests();
});
