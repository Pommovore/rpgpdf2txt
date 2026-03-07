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

async function clearCache() {
    if (!confirm("Voulez-vous vraiment vider l'ensemble du cache ? Cela supprimera toutes les extractions déjà réalisées et forcera un nouveau calcul pour les futurs PDF identiques.")) {
        return;
    }
    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/admin/cache`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            alert(`Cache vidé avec succès (${data.deleted_count} entrées supprimées).`);
        } else {
            const data = await response.json();
            alert('Erreur: ' + (data.detail || 'Impossible de vider le cache'));
        }
    } catch (err) {
        console.error("Échec lors du vidage du cache", err);
        alert("Erreur de connexion lors du nettoyage du cache.");
    }
}

async function clearQueue() {
    if (!confirm("Voulez-vous annuler toutes les extractions en attente ou en cours ? Les webhooks vont recevoir une notification de maintenance technique.")) {
        return;
    }
    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/admin/queue`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            alert(`File d'attente vidée (${data.interrupted_count} extractions annulées).`);
        } else {
            const data = await response.json();
            alert('Erreur: ' + (data.detail || 'Impossible de vider la file'));
        }
    } catch (err) {
        console.error("Échec lors du vidage de la file d'attente", err);
        alert("Erreur de connexion lors de l'annulation de la file d'attente.");
    }
}

async function loadUsers() {
    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/admin/users`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401 || response.status === 403) {
            alert('Accès non autorisé. Veuillez vous connecter en tant qu\'administrateur.');
            window.location.href = `${APP_PREFIX}/login`;
            return;
        }

        const users = await response.json();
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';

        users.forEach(user => {
            const tr = document.createElement('tr');

            let statusBadge = user.is_validated
                ? '<span class="badge bg-success">Validé</span>'
                : '<span class="badge bg-warning text-dark">En attente</span>';

            let actionBtn = '';
            if (!user.is_validated) {
                actionBtn = `<button class="btn btn-sm btn-success" onclick="validateUser(${user.id})">Valider</button>`;
            } else {
                actionBtn = `<button class="btn btn-sm btn-secondary" disabled>Validé</button>`;
            }

            tr.innerHTML = `
                <td>${user.id}</td>
                <td>${user.email}</td>
                <td><span class="badge bg-info">${user.role}</span></td>
                <td>${statusBadge}</td>
                <td><input type="text" class="form-control form-control-sm bg-dark text-muted border-secondary" value="${user.api_token || '-'}" readonly style="width: 150px;"></td>
                <td><code>${user.directory_name || '-'}</code></td>
                <td>${actionBtn}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Échec du chargement des utilisateurs', err);
    }
}

async function validateUser(userId) {
    try {
        const response = await fetch(`${APP_PREFIX}/api/v1/admin/users/${userId}/validate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            loadUsers(); // recharger le tableau
        } else {
            const data = await response.json();
            alert('Erreur: ' + (data.detail || 'Échec de la validation'));
        }
    } catch (err) {
        console.error('Échec de validation de l\'utilisateur', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadUsers();
});
