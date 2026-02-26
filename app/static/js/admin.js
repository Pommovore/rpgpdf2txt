const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = '/login';
}

function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
}

async function loadUsers() {
    try {
        const response = await fetch('/api/v1/admin/users', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401 || response.status === 403) {
            alert('Accès non autorisé. Veuillez vous connecter en tant qu\'administrateur.');
            window.location.href = '/login';
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
        const response = await fetch(`/api/v1/admin/users/${userId}/validate`, {
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
