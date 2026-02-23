// api.js - Communication avec l'API Django

const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    TIMEOUT: 20000,
    ENDPOINTS: {
        // Authentification
        LOGIN: '/api/users/login/',
        LOGOUT: '/api/auth/logout/',
        REFRESH_TOKEN: '/api/token/refresh/',

        // Utilisateurs
        USERS: '/api/utilisateurs/',
        USER_PROFILE: '/api/users/profile/',

        // Stocks
        STOCKS: '/api/lots/',
        STOCK_STATS: '/api/lots/stats/',
        STOCK_MOVEMENTS: '/api/mouvements/',
        STOCK_ALERTS: '/api/alertes/',

        // Produits
        PRODUCTS: '/api/produits/',
        PRODUCT_CATEGORIES: '/api/products/categories/',

        // Livraisons
        DELIVERIES: '/api/livraisons/',
        DELIVERY_TRACKING: '/api/livraisons/tracking/',

        // Ventes
        SALES: '/api/ventes/',
        SALES_STATS: '/api/ventes/stats/',

        // Prévisions
        FORECASTS: '/api/previsions/',

        // Rapports
        REPORTS: '/api/reports/'
    }
};

function getDemoData() {
    try {
        const v3 = localStorage.getItem('demo_data_v3');
        if (v3) return JSON.parse(v3);
        const v2 = localStorage.getItem('demo_data_v2');
        if (v2) return JSON.parse(v2);
        return JSON.parse(localStorage.getItem('demo_data_v1') || '{}');
    } catch {
        return {};
    }
}

function saveDemoData(data) {
    localStorage.setItem('demo_data_v3', JSON.stringify(data));
}

async function demoRequest(endpoint, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const path = endpoint.split('?')[0];
    const queryString = endpoint.includes('?') ? endpoint.split('?')[1] : '';
    const data = getDemoData();

    const jsonBody = () => {
        try {
            return options.body ? JSON.parse(options.body) : {};
        } catch {
            return {};
        }
    };

    if (path.startsWith('/api/produits/')) {
        return data.produits || [];
    }

    if (path.startsWith('/api/categories/')) {
        return data.categories || [];
    }

    if (path.startsWith('/api/entrepots/')) {
        return data.entrepots || [];
    }

    if (path.startsWith('/api/lots/')) {
        if (method === 'GET') return data.lots || [];
        if (method === 'POST') {
            const payload = jsonBody();
            const nextId = Math.max(0, ...(data.lots || []).map(l => l.id_lot)) + 1;
            const lot = { id_lot: nextId, ...payload };
            data.lots = [...(data.lots || []), lot];
            saveDemoData(data);
            return lot;
        }
        const match = path.match(/\/api\/lots\/(\d+)\/?$/);
        if (match && method === 'PUT') {
            const id = Number(match[1]);
            const payload = jsonBody();
            data.lots = (data.lots || []).map(l => (l.id_lot === id ? { ...l, ...payload } : l));
            saveDemoData(data);
            return data.lots.find(l => l.id_lot === id) || payload;
        }
        if (match && method === 'DELETE') {
            const id = Number(match[1]);
            data.lots = (data.lots || []).filter(l => l.id_lot !== id);
            saveDemoData(data);
            return { success: true };
        }
        return data.lots || [];
    }

    if (path.startsWith('/api/mouvements/')) {
        return data.mouvements || [];
    }

    if (path === '/api/approvisionnements/') {
        if (method === 'GET') return data.approvisionnements || [];
        if (method === 'POST') {
            const payload = jsonBody();
            const nextId = Math.max(0, ...(data.approvisionnements || []).map(a => a.id_approvisionnement || 0)) + 1;
            const produits = data.produits || [];
            const lignes = (payload.lignes || []).map((l, idx) => {
                const produit = produits.find(p => p.id_produit === Number(l.produit)) || {};
                return {
                    id_ligne: (nextId * 100) + idx + 1,
                    produit_id: l.produit,
                    produit_nom: produit.nom_produit || l.produit_nom || 'Produit',
                    produit_unite: produit.unite || 'kg',
                    quantite_commandee: Number(l.quantite_commandee || l.quantite || 0),
                    quantite_recue: 0,
                    statut_ligne: 'pending'
                };
            });
            const totalCommandee = lignes.reduce((sum, l) => sum + (Number(l.quantite_commandee) || 0), 0);
            const approv = {
                id_approvisionnement: nextId,
                numero_commande: payload.numero_commande || `APP-20260223-${String(nextId).padStart(4, '0')}`,
                fournisseur: payload.fournisseur || 'Fournisseur demo',
                statut_approvisionnement: 'pending',
                date_commande: payload.date_commande || new Date().toISOString(),
                date_livraison_attendue: payload.date_livraison_attendue || new Date().toISOString(),
                entrepot_nom: payload.entrepot_nom || 'Entrepot Central',
                gestionnaire_nom: payload.gestionnaire_nom || 'Gestionnaire Logistique',
                total_quantite_commandee: totalCommandee,
                total_quantite_recue: 0,
                lignes
            };
            data.approvisionnements = [...(data.approvisionnements || []), approv];
            saveDemoData(data);
            return approv;
        }
    }

    if (path === '/api/approvisionnements/stats/') {
        const approvs = data.approvisionnements || [];
        const stats = {
            total_pending: approvs.filter(a => a.statut_approvisionnement === 'pending').length,
            total_in_transit: approvs.filter(a => a.statut_approvisionnement === 'in_transit').length,
            total_delivered: approvs.filter(a => a.statut_approvisionnement === 'delivered').length,
            total_cancelled: approvs.filter(a => a.statut_approvisionnement === 'cancelled').length
        };
        return stats;
    }

    const approvActionMatch = path.match(/\/api\/approvisionnements\/(\d+)\/(mark_in_transit|mark_delivered|cancel)\/?$/);
    if (approvActionMatch && method === 'POST') {
        const id = Number(approvActionMatch[1]);
        const action = approvActionMatch[2];
        const payload = jsonBody();
        data.approvisionnements = (data.approvisionnements || []).map(a => {
            if (a.id_approvisionnement !== id) return a;
            if (action === 'mark_in_transit') {
                return { ...a, statut_approvisionnement: 'in_transit' };
            }
            if (action === 'cancel') {
                return { ...a, statut_approvisionnement: 'cancelled', notes: payload.raison || a.notes };
            }
            if (action === 'mark_delivered') {
                const lignes = (a.lignes || []).map(l => {
                    const rec = (payload.lignes_receptions || []).find(r => Number(r.id_ligne) === Number(l.id_ligne));
                    const quantiteRecue = rec ? Number(rec.quantite_recue || 0) : Number(l.quantite_commandee || 0);
                    return { ...l, quantite_recue: quantiteRecue, statut_ligne: quantiteRecue >= Number(l.quantite_commandee || 0) ? 'delivered' : 'partial' };
                });
                const totalRecue = lignes.reduce((sum, l) => sum + (Number(l.quantite_recue) || 0), 0);
                return { ...a, statut_approvisionnement: 'delivered', total_quantite_recue: totalRecue, lignes };
            }
            return a;
        });
        saveDemoData(data);
        return { success: true };
    }

    if (path === '/api/ventes/') {
        return data.ventes || [];
    }

    if (path === '/api/ventes/creer_avec_lignes/' && method === 'POST') {
        const payload = jsonBody();
        const nextId = Math.max(500, ...(data.ventes || []).map(v => v.id_vente)) + 1;
        const total = (payload.lignes || []).reduce((sum, l) => sum + (Number(l.quantite_vendue || 0) * Number(l.prix_unitaire || 0)), 0);
        const vente = {
            id_vente: nextId,
            numero_facture: `FAC-20260218-${String(nextId).slice(-5).padStart(5, '0')}`,
            nom_client: payload.nom_client || 'Client demo',
            montant_total: total,
            statut_vente: 'brouillon',
            date_vente: new Date().toISOString()
        };
        data.ventes = [...(data.ventes || []), vente];
        saveDemoData(data);
        return vente;
    }

    const venteMatch = path.match(/\/api\/ventes\/(\d+)\/(valider|annuler)\/?$/);
    if (venteMatch && method === 'POST') {
        const id = Number(venteMatch[1]);
        const action = venteMatch[2];
        data.ventes = (data.ventes || []).map(v => {
            if (v.id_vente !== id) return v;
            return { ...v, statut_vente: action === 'valider' ? 'validée' : 'annulée' };
        });
        saveDemoData(data);
        return { success: true };
    }

    if (path.startsWith('/api/livraisons/')) {
        return data.livraisons || [];
    }

    if (path.startsWith('/api/notifications/')) {
        data.notifications = data.notifications || [];

        if (path === '/api/notifications/generer_alertes/' && method === 'POST') {
            const alertes = data.previsions_alertes || [];
            const nextId = Math.max(0, ...(data.notifications || []).map(n => n.id_notification || 0)) + 1;

            const nouvelles = alertes
                .filter(a => a.niveau === 'danger')
                .map((a, idx) => ({
                    id_notification: nextId + idx,
                    type_notification: `alerte_${a.type}`,
                    message: `⚠️ ALERTE ${a.produit_nom}: ${a.message}`,
                    date_envoi: new Date().toISOString()
                }));

            data.notifications = [...data.notifications, ...nouvelles];
            saveDemoData(data);
            return { status: 'ok', notifications_creees: nouvelles.length };
        }

        if (method === 'POST' && path === '/api/notifications/') {
            const payload = jsonBody();
            const nextId = Math.max(0, ...(data.notifications || []).map(n => n.id_notification || 0)) + 1;
            const notif = {
                id_notification: nextId,
                ...payload,
                date_envoi: payload.date_envoi || new Date().toISOString()
            };
            data.notifications = [...data.notifications, notif];
            saveDemoData(data);
            return notif;
        }

        if (method === 'GET' && queryString.includes('utilisateur=')) {
            const match = queryString.match(/utilisateur=(\d+)/);
            if (match) {
                const userId = Number(match[1]);
                return data.notifications.filter(n => !n.utilisateur || n.utilisateur === userId);
            }
        }

        return data.notifications || [];
    }

    if (path.startsWith('/api/previsions/tous_resumés/')) {
        return data.previsions || [];
    }

    if (path.startsWith('/api/previsions/risques_peremption/')) {
        return data.risques_peremption || [];
    }

    if (path.startsWith('/api/previsions/predictions_ml/')) {
        return data.predictions_ml || [];
    }

    if (path.startsWith('/api/previsions/alertes_critiques/')) {
        return data.previsions_alertes || [];
    }

    if (path.startsWith('/api/utilisateurs/')) {
        return data.utilisateurs || [];
    }

    return [];
}

window.demoApiRequest = demoRequest;

class API {
    constructor() {
        this.token = localStorage.getItem('token') || localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refreshToken') || localStorage.getItem('refresh_token');
    }

    // Méthode générique pour les requêtes
    async request(endpoint, options = {}) {
        const url = `${API_CONFIG.BASE_URL}${endpoint}`;

        const isAuthEndpoint = endpoint.includes('/users/login/') || endpoint.includes('/token/refresh/');

        if (localStorage.getItem('demo_mode') === 'true' && !isAuthEndpoint) {
            return demoRequest(endpoint, options);
        }

        const defaultHeaders = {
            'Content-Type': 'application/json'
        };

        const token = this.token || localStorage.getItem('token') || localStorage.getItem('access_token');
        if (token && !isAuthEndpoint) {
            defaultHeaders['Authorization'] = `Bearer ${token}`;
        }

        const finalOptions = {
            ...options,
            headers: { ...defaultHeaders, ...(options.headers || {}) },
            timeout: API_CONFIG.TIMEOUT
        };

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);

            const response = await fetch(url, {
                ...finalOptions,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // Gérer les réponses non-OK
            if (!response.ok) {
                // Tentative de refresh token si 401
                if (response.status === 401 && this.refreshToken && !endpoint.includes('/auth/refresh/')) {
                    const refreshed = await this.refreshAccessToken();
                    if (refreshed) {
                        // Réessayer la requête avec le nouveau token
                        finalOptions.headers.Authorization = `Bearer ${this.token}`;
                        return this.request(endpoint, finalOptions);
                    }
                }

                const error = await this.parseError(response);
                throw error;
            }

            // Parser la réponse
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }

        } catch (error) {
            if (error && error.name !== 'AbortError') {
                console.error(`API Request failed (${endpoint}):`, error);
            }
            throw this.normalizeError(error);
        }
    }

    async parseError(response) {
        try {
            const errorData = await response.json();
            return {
                status: response.status,
                message: errorData.detail || errorData.message || `HTTP ${response.status}`,
                data: errorData
            };
        } catch {
            return {
                status: response.status,
                message: `HTTP ${response.status}: ${response.statusText}`
            };
        }
    }

    normalizeError(error) {
        if (error.name === 'AbortError') {
            return {
                status: 408,
                message: 'Request timeout'
            };
        }

        if (error.status) {
            return error;
        }

        return {
            status: 0,
            message: 'Network error or server unreachable'
        };
    }

    // Authentification
    async login(credentials) {
        // Nettoyer les anciens tokens pour éviter les conflits
        this.clearTokens();

        try {
            const data = await this.request(API_CONFIG.ENDPOINTS.LOGIN, {
                method: 'POST',
                body: JSON.stringify(credentials)
            });

            // Stocker les tokens
            this.setTokens(data.access, data.refresh);

            return {
                success: true,
                tokens: {
                    access: data.access,
                    refresh: data.refresh
                },
                user: data.user
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async logout() {
        try {
            await this.request(API_CONFIG.ENDPOINTS.LOGOUT, {
                method: 'POST'
            });
        } finally {
            this.clearTokens();
        }
    }

    async refreshAccessToken() {
        this.refreshToken = this.refreshToken || localStorage.getItem('refreshToken') || localStorage.getItem('refresh_token');
        if (!this.refreshToken) return false;

        try {
            const data = await this.request(API_CONFIG.ENDPOINTS.REFRESH_TOKEN, {
                method: 'POST',
                body: JSON.stringify({ refresh: this.refreshToken })
            });

            this.setTokens(data.access, this.refreshToken);
            return true;

        } catch (error) {
            this.clearTokens();
            return false;
        }
    }

    // Gestion des tokens
    setTokens(accessToken, refreshToken) {
        this.token = accessToken;
        this.refreshToken = refreshToken;

        localStorage.setItem('token', accessToken);
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        localStorage.setItem('refresh_token', refreshToken);

        // Stocker l'expiration (1 heure par défaut)
        const expiry = new Date();
        expiry.setHours(expiry.getHours() + 1);
        localStorage.setItem('tokenExpiry', expiry.toISOString());
    }

    clearTokens() {
        this.token = null;
        this.refreshToken = null;

        localStorage.removeItem('token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('tokenExpiry');
        localStorage.removeItem('userData');
    }

    isTokenValid() {
        const expiry = localStorage.getItem('tokenExpiry');
        if (!expiry || !this.token) return false;

        return new Date(expiry) > new Date();
    }

    // Profil utilisateur
    async getUserProfile() {
        try {
            const profile = await this.request(API_CONFIG.ENDPOINTS.USER_PROFILE);
            localStorage.setItem('userData', JSON.stringify(profile));
            return profile;
        } catch (error) {
            console.warn('Could not fetch user profile:', error);
            return null;
        }
    }

    // Stocks
    async getStocks(params = {}) {
        const query = new URLSearchParams(params).toString();
        const endpoint = query ? `${API_CONFIG.ENDPOINTS.STOCKS}?${query}` : API_CONFIG.ENDPOINTS.STOCKS;
        return this.request(endpoint);
    }

    async getStock(id) {
        return this.request(`${API_CONFIG.ENDPOINTS.STOCKS}${id}/`);
    }

    async createStock(stockData) {
        return this.request(API_CONFIG.ENDPOINTS.STOCKS, {
            method: 'POST',
            body: JSON.stringify(stockData)
        });
    }

    async updateStock(id, stockData) {
        return this.request(`${API_CONFIG.ENDPOINTS.STOCKS}${id}/`, {
            method: 'PUT',
            body: JSON.stringify(stockData)
        });
    }

    async deleteStock(id) {
        return this.request(`${API_CONFIG.ENDPOINTS.STOCKS}${id}/`, {
            method: 'DELETE'
        });
    }

    async getStockStats() {
        return this.request(API_CONFIG.ENDPOINTS.STOCK_STATS);
    }

    async getStockMovements(params = {}) {
        const query = new URLSearchParams(params).toString();
        const endpoint = query ? `${API_CONFIG.ENDPOINTS.STOCK_MOVEMENTS}?${query}` : API_CONFIG.ENDPOINTS.STOCK_MOVEMENTS;
        return this.request(endpoint);
    }

    async getStockAlerts() {
        return this.request(API_CONFIG.ENDPOINTS.STOCK_ALERTS);
    }

    // Produits
    async getProducts(params = {}) {
        const query = new URLSearchParams(params).toString();
        const endpoint = query ? `${API_CONFIG.ENDPOINTS.PRODUCTS}?${query}` : API_CONFIG.ENDPOINTS.PRODUCTS;
        return this.request(endpoint);
    }

    async getProductCategories() {
        return this.request(API_CONFIG.ENDPOINTS.PRODUCT_CATEGORIES);
    }

    // Livraisons
    async getDeliveries(params = {}) {
        const query = new URLSearchParams(params).toString();
        const endpoint = query ? `${API_CONFIG.ENDPOINTS.DELIVERIES}?${query}` : API_CONFIG.ENDPOINTS.DELIVERIES;
        return this.request(endpoint);
    }

    // Ventes
    async getSales(params = {}) {
        const query = new URLSearchParams(params).toString();
        const endpoint = query ? `${API_CONFIG.ENDPOINTS.SALES}?${query}` : API_CONFIG.ENDPOINTS.SALES;
        return this.request(endpoint);
    }

    // Méthodes utilitaires
    async uploadFile(endpoint, file, fieldName = 'file') {
        const formData = new FormData();
        formData.append(fieldName, file);

        return this.request(endpoint, {
            method: 'POST',
            headers: {
                'Authorization': this.token ? `Bearer ${this.token}` : ''
            },
            body: formData
        });
    }

    // Simulation pour le développement
    async simulateRequest(data, delay = 1000, success = true) {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (success) {
                    resolve({
                        success: true,
                        data: data,
                        timestamp: new Date().toISOString()
                    });
                } else {
                    reject({
                        status: 500,
                        message: 'Simulated error'
                    });
                }
            }, delay);
        });
    }
}

// Singleton instance
const api = new API();

// Exporter pour utilisation globale
window.API = API;
window.api = api;

// Helper pour les appels API courants
window.fetchAPI = async (endpoint, options = {}) => {
    return api.request(endpoint, options);
};

// Initialiser l'API au chargement
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier le token au démarrage
    if (api.token && !api.isTokenValid()) {
        api.refreshAccessToken().catch(() => {
            // Si le refresh échoue, déconnecter
            api.clearTokens();
        });
    }

    console.log('API module initialized');
});
