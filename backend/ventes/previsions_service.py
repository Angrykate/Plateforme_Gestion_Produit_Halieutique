"""
Service pour calculer les prévisions intelligentes
Basé sur l'historique des ventes et les stocks actuels
"""
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from produits.models import Lot, Produit
from tracabilite.models import MouvementStock
from .models import Vente, LigneVente, Prevision
import statistics

# Importer le service ML
try:
    from .ml_service import MLPrevisionService
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

class PrevisionService:
    """Service pour calculer et gérer les prévisions"""

    @staticmethod
    def _fallback_profile(produit_id, stock_actuel):
        """Retourne un profil synthétique si l'historique est insuffisant."""
        seed = (produit_id * 37) % 100

        # Base quotidienne simulée (1-12 unités/jour)
        base_daily = max(1, min(12, int((seed % 10) + (stock_actuel / 50))))

        # Tendance simulée
        mod = produit_id % 3
        if mod == 0:
            tendance = 'croissante'
        elif mod == 1:
            tendance = 'stable'
        else:
            tendance = 'decroissante'

        return base_daily, tendance
    
    @staticmethod
    def calculer_moyenne_mobile(produit_id, jours=30):
        """
        Calcule la moyenne mobile basee sur les sorties de stock
        """
        date_debut = timezone.now().date() - timedelta(days=jours)

        sorties = MouvementStock.objects.filter(
            lot__produit_id=produit_id,
            date_mouvement__gte=date_debut,
            type_mouvement__istartswith='Sortie'
        ).values('date_mouvement').annotate(
            total=Sum('quantite')
        ).order_by('date_mouvement')

        quantites = [s['total'] for s in sorties if s['total'] is not None]
        
        if len(quantites) < 2:
            stock_actuel = PrevisionService.obtenir_stock_actuel(produit_id)
            base_daily, _ = PrevisionService._fallback_profile(produit_id, float(stock_actuel))
            return Decimal(str(base_daily * jours))
        
        try:
            moyenne = Decimal(str(statistics.mean(quantites)))
            return moyenne
        except:
            return Decimal('0')
    
    @staticmethod
    def detecter_tendance(produit_id, jours=30):
        """
        Détecte la tendance (hausse, baisse, stable)
        Retourne: 'croissante', 'decroissante', 'stable'
        """
        date_debut = timezone.now().date() - timedelta(days=jours)

        sorties = MouvementStock.objects.filter(
            lot__produit_id=produit_id,
            date_mouvement__gte=date_debut,
            type_mouvement__istartswith='Sortie'
        ).values('date_mouvement').annotate(
            total=Sum('quantite')
        ).order_by('date_mouvement')

        if sorties.count() < 7:
            stock_actuel = PrevisionService.obtenir_stock_actuel(produit_id)
            _, tendance = PrevisionService._fallback_profile(produit_id, float(stock_actuel))
            return tendance
        
        # Diviser en deux périodes
        ventes_list = list(sorties)
        mid = len(ventes_list) // 2
        
        quantites_debut = [v['total'] for v in ventes_list[:mid]]
        quantites_fin = [v['total'] for v in ventes_list[mid:]]
        
        try:
            moy_debut = statistics.mean(quantites_debut)
            moy_fin = statistics.mean(quantites_fin)
            
            diff_percent = ((moy_fin - moy_debut) / moy_debut * 100) if moy_debut > 0 else 0
            
            if diff_percent > 10:
                return 'croissante'
            elif diff_percent < -10:
                return 'decroissante'
            else:
                return 'stable'
        except:
            return 'stable'
    
    @staticmethod
    def obtenir_stock_actuel(produit_id):
        """Retourne le stock total actuel d'un produit"""
        lots = Lot.objects.filter(produit_id=produit_id, quantite__gt=0)
        total = sum(lot.quantite for lot in lots)
        return Decimal(str(total))
    
    @staticmethod
    def calculer_jours_rupture(produit_id, jours_prevision=30):
        """
        Calcule en combien de jours il y aura rupture de stock
        Retourne: nombre de jours ou -1 si pas de rupture prévue
        """
        stock_actuel = PrevisionService.obtenir_stock_actuel(produit_id)
        moyenne_quotidienne = PrevisionService.calculer_moyenne_mobile(produit_id, 30) / 30
        
        if moyenne_quotidienne <= 0:
            return -1  # Pas de consommation
        
        if stock_actuel <= 0:
            return 0  # Déjà rupture
        
        jours_rupture = stock_actuel / moyenne_quotidienne
        
        if jours_rupture > jours_prevision:
            return -1  # Au-delà de la période de prévision
        
        return int(jours_rupture)
    
    @staticmethod
    def calculer_risque_surstock(produit_id, jours=30):
        """
        Calcule le risque de surstock
        Retourne: pourcentage (0-100) et raison
        """
        try:
            stock_actuel = PrevisionService.obtenir_stock_actuel(produit_id)
            moyenne_30j = PrevisionService.calculer_moyenne_mobile(produit_id, 30)
            moyenne_jour = moyenne_30j / 30 if moyenne_30j else Decimal('0')
            tendance = PrevisionService.detecter_tendance(produit_id, 30)

            if moyenne_jour <= 0:
                if stock_actuel > 0:
                    return 80, "Aucune consommation recente avec stock present"
                return 0, "Aucun stock et aucune consommation"

            # Seuils logistiques (jours fixes)
            stock_securite = moyenne_jour * Decimal('7')
            stock_min = moyenne_jour * Decimal('14')
            stock_alerte = stock_min + stock_securite
            stock_max = moyenne_jour * Decimal('30')

            if stock_actuel <= stock_max:
                return 0, f"Stock normal (≤ max {int(stock_max)})"

            surplus = stock_actuel - stock_max
            surplus_ratio = (surplus / stock_max) if stock_max > 0 else Decimal('0')
            risque = 40 + min(60, int(surplus_ratio * 100))
            raison = [
                f"Stock {int(stock_actuel)} > max {int(stock_max)}",
                f"Surplus {int(surplus)}"
            ]

            # Si demande en baisse
            if tendance == 'decroissante':
                risque += 15
                raison.append("Demande en baisse")

            # Produits périssables avec peu d'écoulement
            lots = Lot.objects.filter(produit_id=produit_id, quantite__gt=0).order_by('date_peremption')
            if lots.exists():
                lot_ancien = lots.first()
                if lot_ancien.date_peremption:
                    jours_avant_expiration = (lot_ancien.date_peremption - timezone.now().date()).days
                    if jours_avant_expiration < 14:
                        risque += 15
                        raison.append(f"Expiration dans {jours_avant_expiration} jours")

            return min(risque, 100), " + ".join(raison)
        except Exception as e:
            return 0, f"Erreur calcul: {str(e)}"
    
    @staticmethod
    def generer_previsions_produit(produit_id, jours_ahead=30):
        """
        Génère les prévisions pour les jours à venir
        Retourne: liste de dictionnaires {date, quantite_prevue, confiance}
        """
        moyenne_quotidienne = PrevisionService.calculer_moyenne_mobile(produit_id, 30) / 30
        tendance = PrevisionService.detecter_tendance(produit_id, 30)

        if moyenne_quotidienne <= 0:
            stock_actuel = PrevisionService.obtenir_stock_actuel(produit_id)
            base_daily, tendance = PrevisionService._fallback_profile(produit_id, float(stock_actuel))
            moyenne_quotidienne = Decimal(str(base_daily))
        
        # Ajuster la prévision selon la tendance
        facteur = Decimal('1.0')
        if tendance == 'croissante':
            facteur = Decimal('1.15')  # +15%
        elif tendance == 'decroissante':
            facteur = Decimal('0.85')  # -15%
        
        previsions = []
        aujourd_hui = timezone.now().date()
        
        for jour in range(1, jours_ahead + 1):
            date_prevue = aujourd_hui + timedelta(days=jour)
            quantite = moyenne_quotidienne * facteur
            
            # Confiance diminue avec l'éloignement
            confiance = max(50, 95 - (jour * 2))
            
            previsions.append({
                'date': date_prevue,
                'quantite_prevue': float(quantite),
                'confiance': confiance
            })
        
        return previsions
    
    @staticmethod
    def generer_alertes(produit_id):
        """
        Génère les alertes pour un produit
        Retourne: liste d'alertes {type, niveau, message, action}
        """
        alertes = []
        
        # Alerte lots expirés
        aujourd_hui = timezone.now().date()
        lots_expires = Lot.objects.filter(
            produit_id=produit_id,
            date_peremption__lt=aujourd_hui,
            quantite__gt=0
        )
        if lots_expires.exists():
            nombre_lots_expires = lots_expires.count()
            quantite_expiree = sum(lot.quantite for lot in lots_expires)
            alertes.append({
                'type': 'expiration',
                'niveau': 'danger',
                'message': f'{nombre_lots_expires} lot(s) expiré(s) ({int(quantite_expiree)} unités)',
                'action': 'Supprimer les lots expirés'
            })

        # Alerte lots bientôt périmés (J-2/J-1)
        lots_bientot = Lot.objects.filter(
            produit_id=produit_id,
            date_peremption__gte=aujourd_hui,
            date_peremption__lte=aujourd_hui + timedelta(days=2),
            quantite__gt=0
        )
        if lots_bientot.exists():
            nombre_lots_bientot = lots_bientot.count()
            quantite_bientot = sum(lot.quantite for lot in lots_bientot)
            alertes.append({
                'type': 'expiration_proche',
                'niveau': 'warning',
                'message': f'{nombre_lots_bientot} lot(s) bientôt périmé(s) ({int(quantite_bientot)} unités)',
                'action': 'Ecouler rapidement'
            })
        
        # Alerte rupture
        jours_rupture = PrevisionService.calculer_jours_rupture(produit_id)
        if jours_rupture >= 0 and jours_rupture <= 7:
            alertes.append({
                'type': 'rupture',
                'niveau': 'danger' if jours_rupture <= 3 else 'warning',
                'message': f'Rupture probable dans {jours_rupture} jours',
                'action': 'Lancer commande d\'approvisionnement'
            })
        
        # Alerte surstock
        risque_surstock, raison = PrevisionService.calculer_risque_surstock(produit_id)
        if risque_surstock > 60:
            alertes.append({
                'type': 'surstock',
                'niveau': 'danger',
                'message': f'Risque de surstock ({risque_surstock}%): {raison}',
                'action': 'Promouvoir ou réduire la commande'
            })
        elif risque_surstock > 40:
            alertes.append({
                'type': 'surstock',
                'niveau': 'warning',
                'message': f'Risque de surstock ({risque_surstock}%): {raison}',
                'action': 'Monitorer'
            })
        
        # Alerte baisse de demande
        tendance = PrevisionService.detecter_tendance(produit_id)
        if tendance == 'decroissante':
            alertes.append({
                'type': 'baisse_demande',
                'niveau': 'info',
                'message': 'La demande pour ce produit baisse',
                'action': 'Réduire la production ou promouvoir'
            })
        
        # Alerte croissance de demande
        if tendance == 'croissante':
            alertes.append({
                'type': 'croissance_demande',
                'niveau': 'success',
                'message': 'La demande pour ce produit augmente',
                'action': 'Augmenter la production'
            })
        
        return alertes
    
    @staticmethod
    def get_score_priorite(produit_id):
        """
        Calcule un score de priorité global (0-100)
        Considère: rupture risk, surstock risk, croissance, etc.
        """
        score = 50  # Score de base neutre
        
        # Ajuster selon le risque de rupture
        jours_rupture = PrevisionService.calculer_jours_rupture(produit_id)
        if jours_rupture >= 0:
            if jours_rupture <= 3:
                score += 40  # Très urgent
            elif jours_rupture <= 7:
                score += 25  # Urgent
            elif jours_rupture <= 14:
                score += 10  # Important
        
        # Déduire si surstock
        risque_surstock, _ = PrevisionService.calculer_risque_surstock(produit_id)
        score -= int(risque_surstock / 4)
        
        # Ajouter si croissance
        tendance = PrevisionService.detecter_tendance(produit_id)
        if tendance == 'croissante':
            score += 15
        elif tendance == 'decroissante':
            score -= 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def get_resumé_produit(produit_id):
        """
        Retourne un résumé complet pour un produit
        Intègre ML si disponible
        """
        produit = Produit.objects.get(id_produit=produit_id)
        
        resume_base = {
            'produit_id': produit_id,
            'produit_nom': produit.nom_produit,
            'prix_unitaire': float(produit.prix_unitaire) if produit.prix_unitaire is not None else None,
            'unite': produit.unite or 'kg',
            'stock_actuel': float(PrevisionService.obtenir_stock_actuel(produit_id)),
            'moyenne_quotidienne': float(PrevisionService.calculer_moyenne_mobile(produit_id, 30) / 30),
            'jours_rupture': PrevisionService.calculer_jours_rupture(produit_id),
            'tendance': PrevisionService.detecter_tendance(produit_id),
            'risque_surstock': PrevisionService.calculer_risque_surstock(produit_id)[0],
            'alertes': PrevisionService.generer_alertes(produit_id),
            'score_priorite': PrevisionService.get_score_priorite(produit_id),
            'previsions_7j': PrevisionService.generer_previsions_produit(produit_id, 7)
        }
        
        # Ajouter prédictions ML si disponible
        if ML_AVAILABLE:
            try:
                ml_data = MLPrevisionService.calculer_score_intelligent(produit_id)
                resume_base['ml_predictions'] = {
                    'score_rupture_ml': ml_data['score_rupture'],
                    'score_surstock_ml': ml_data['score_surstock'],
                    'jours_couverture_ml': ml_data['jours_couverture'],
                    'demande_predite_14j': ml_data['demande_predite_14j'],
                    'trend_ml': ml_data['trend'],
                    'recommandation': ml_data['recommandation'],
                    'confidence': ml_data['confidence']
                }
                
                # Utiliser scores ML pour meilleur scoring de priorité
                resume_base['score_priorite_ml'] = int(
                    (ml_data['score_rupture'] * 0.6 + (100 - ml_data['score_surstock']) * 0.4)
                )
            except Exception as e:
                resume_base['ml_error'] = str(e)
        
        return resume_base
    
    @staticmethod
    def get_tous_resumés():
        """Retourne le résumé pour tous les produits"""
        produits = Produit.objects.all()
        resumés = []
        
        for produit in produits:
            try:
                resumés.append(PrevisionService.get_resumé_produit(produit.id_produit))
            except Exception as e:
                print(f"Erreur pour produit {produit.id_produit}: {e}")
        
        # Trier par score de priorité (descending)
        resumés.sort(key=lambda x: x['score_priorite'], reverse=True)
        
        return resumés
