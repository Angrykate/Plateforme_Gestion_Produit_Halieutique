#!/usr/bin/env python
"""
seed_demo_complet.py - Script de démo amélioré et complet
Crée des données réalistes pour la démonstration
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from produits.models import Categorie, Produit, Lot
from ventes.models import Vente, LigneVente
from logistique.models import Approvisionnement, ApprovisionnementLigne, Livraison, LivraisonLigne
from tracabilite.models import MouvementStock, Alerte
from users.models import Utilisateur

print("=" * 80)
print("🎬 CRÉATION MODE DÉMO AMÉLIORÉ")
print("=" * 80)

# ============================================================================
# NETTOYAGE
# ============================================================================
print("\n🗑️  Nettoyage des anciennes données démo...")
Alerte.objects.all().delete()
MouvementStock.objects.all().delete()
LivraisonLigne.objects.all().delete()
Livraison.objects.all().delete()
LigneVente.objects.all().delete()
Vente.objects.all().delete()
ApprovisionnementLigne.objects.all().delete()
Approvisionnement.objects.all().delete()
Lot.objects.all().delete()
print("   ✅ Anciennes données supprimées")

# ============================================================================
# RÉCUPÉRATION DES DONNÉES DE BASE
# ============================================================================
produits = list(Produit.objects.all().order_by('id_produit'))
categories = list(Categorie.objects.all())
users = list(Utilisateur.objects.all())

if not produits:
    print("❌ Erreur: Aucun produit trouvé. Exécutez populate_real_data.py d'abord.")
    sys.exit(1)

if not users:
    print("❌ Erreur: Aucun utilisateur trouvé. Exécutez create_halieutique_users.py d'abord.")
    sys.exit(1)

admin = users[0]
gestionnaire_stock = users[1] if len(users) > 1 else admin
gestionnaire_log = users[2] if len(users) > 2 else admin

print(f"\n📦 {len(produits)} produits disponibles")
print(f"👥 {len(users)} utilisateurs disponibles")

# ============================================================================
# 1. CRÉATION DES LOTS AVEC ÉTATS VARIÉS
# ============================================================================
print("\n" + "=" * 80)
print("📦 CRÉATION DES LOTS (stock varié)")
print("=" * 80)

today = datetime.now().date()
lots_created = []

# Définir les scénarios par produit
scenarios = [
    # RUPTURE (stock très faible = 1, car les lots avec 0 sont auto-supprimés)
    {'type': 'rupture', 'stock': 1, 'color': '🔴'},
    {'type': 'rupture', 'stock': 1, 'color': '🔴'},
    {'type': 'rupture', 'stock': 1, 'color': '🔴'},
    {'type': 'rupture', 'stock': 1, 'color': '🔴'},
    
    # STOCK FAIBLE (1-20)
    {'type': 'stock_faible', 'stock': (5, 20), 'color': '🟡'},
    {'type': 'stock_faible', 'stock': (5, 20), 'color': '🟡'},
    {'type': 'stock_faible', 'stock': (5, 20), 'color': '🟡'},
    {'type': 'stock_faible', 'stock': (5, 20), 'color': '🟡'},
    {'type': 'stock_faible', 'stock': (5, 20), 'color': '🟡'},
    
    # PÉRIMÉ ou PROCHE PÉREMPTION (expire dans 1-5 jours)
    {'type': 'perime', 'stock': (10, 50), 'expires': (1, 5), 'color': '🟠'},
    {'type': 'perime', 'stock': (10, 50), 'expires': (1, 5), 'color': '🟠'},
    {'type': 'perime', 'stock': (10, 50), 'expires': (1, 5), 'color': '🟠'},
    
    # STOCK NORMAL (50-200)
    {'type': 'normal', 'stock': (50, 200), 'expires': (10, 30), 'color': '🟢'},
    {'type': 'normal', 'stock': (50, 200), 'expires': (10, 30), 'color': '🟢'},
    {'type': 'normal', 'stock': (50, 200), 'expires': (10, 30), 'color': '🟢'},
    {'type': 'normal', 'stock': (50, 200), 'expires': (10, 30), 'color': '🟢'},
    {'type': 'normal', 'stock': (50, 200), 'expires': (10, 30), 'color': '🟢'},
    
    # SURSTOCK (300-500)
    {'type': 'surstock', 'stock': (300, 500), 'expires': (15, 40), 'color': '🔵'},
    {'type': 'surstock', 'stock': (300, 500), 'expires': (15, 40), 'color': '🔵'},
]

for i, produit in enumerate(produits[:len(scenarios)]):
    scenario = scenarios[i]
    
    # Déterminer la quantité
    if scenario['stock'] == 0:
        quantite = 0
    elif isinstance(scenario['stock'], tuple):
        quantite = random.randint(*scenario['stock'])
    else:
        quantite = scenario['stock']
    
    # Déterminer la date d'expiration
    if 'expires' in scenario:
        jours = random.randint(*scenario['expires'])
        date_expiration = today + timedelta(days=jours)
    else:
        # Produits en rupture ont une date d'expiration passée ou proche
        date_expiration = today + timedelta(days=random.randint(5, 15)) if quantite > 0 else None
    
    # Créer le lot
    lot = Lot.objects.create(
        produit=produit,
        date_reception=today - timedelta(days=random.randint(1, 10)),
        date_peremption=date_expiration,
        quantite=quantite,
        statut_lot='disponible' if quantite > 20 else ('faible' if quantite > 0 else 'epuise'),
        notes=f"LOT-{today.strftime('%Y%m')}-{i+1:03d} - {random.choice(['Pêcherie Douala', 'Aquaculture Kribi', 'Marché Poisson Yaoundé', 'Import Mer SA'])}"
    )
    
    lots_created.append(lot)
    print(f"   {scenario['color']} {produit.nom_produit:30s} - Stock: {quantite:4d} - {scenario['type']:15s} - Expire: {date_expiration or 'N/A'}")

# Créer quelques lots supplémentaires pour les produits restants
for produit in produits[len(scenarios):]:
    quantite = random.randint(30, 150)
    lot = Lot.objects.create(
        produit=produit,
        date_reception=today - timedelta(days=random.randint(1, 10)),
        date_peremption=today + timedelta(days=random.randint(15, 45)),
        quantite=quantite,
        statut_lot='disponible',
        notes=f"LOT-{today.strftime('%Y%m')}-{len(lots_created)+1:03d} - Fournisseur Général"
    )
    lots_created.append(lot)
    print(f"   🟢 {produit.nom_produit:30s} - Stock: {quantite:4d} - normal")

print(f"\n✅ {len(lots_created)} lots créés")

# ============================================================================
# 2. CRÉATION DES APPROVISIONNEMENTS  
# ============================================================================
print("\n" + "=" * 80)
print("📥 CRÉATION DES APPROVISIONNEMENTS")
print("=" * 80)

approvs_created = []
for i in range(5):
    approv = Approvisionnement.objects.create(
        date_livraison_attendue=today + timedelta(days=random.randint(1, 7)),
        fournisseur=random.choice([
            "Pêcherie Douala", "Aquaculture Kribi", 
            "Marché Poisson Yaoundé", "Import Mer SA"
        ]),
        statut_approvisionnement=random.choice(['pending', 'in_transit', 'delivered']),
        gestionnaire_logistique=gestionnaire_log,
        numero_commande=f"CMD-{today.strftime('%Y%m')}-{i+1:03d}",
        notes=f"Approvisionnement #{i+1} - Commande régulière"
    )
    
    # Ajouter 2-4 lignes d'approvisionnement (sans doub lons)
    nb_lignes = random.randint(2, min(4, len(produits)))
    produits_choisis = random.sample(produits, nb_lignes)  # sample() évite les doublons
    
    for produit in produits_choisis:
        quantite = random.randint(50, 200)
        prix = float(produit.prix_unitaire) * 0.6 if produit.prix_unitaire else 1000
        
        ApprovisionnementLigne.objects.create(
            approvisionnement=approv,
            produit=produit,
            quantite_commandee=quantite,
            quantite_recue=quantite if approv.statut_approvisionnement == 'delivered' else 0,
            prix_unitaire=prix
        )
    
    approvs_created.append(approv)
    print(f"   ✅ Approv #{i+1} - {approv.fournisseur} - {approv.statut_approvisionnement}")

print(f"\n✅ {len(approvs_created)} approvisionnements créés")

# ============================================================================
# 3. CRÉATION DES VENTES
# ============================================================================
print("\n" + "=" * 80)
print("💰 CRÉATION DES VENTES")
print("=" * 80)

ventes_created = []
for i in range(12):
    vente = Vente.objects.create(
        date_vente=timezone.now() - timedelta(days=random.randint(0, 30)),
        nom_client=random.choice([
            "Restaurant Le Gourmet", "Hôtel Hilton", "Supermarché Carrefour",
            "Restaurant Chez Marie", "Traiteur Excellence", "Client Particulier"
        ]),
        statut_vente=random.choice(['validée', 'livrée', 'en_cours_livraison']),
        utilisateur=users[min(3, len(users)-1)] if len(users) > 3 else admin,
        numero_facture=f"FACT-{today.strftime('%Y%m')}-{i+1:03d}"
    )
    
    # Ajouter 1-3 lignes de vente
    nb_lignes = random.randint(1, 3)
    
    for j in range(nb_lignes):
        # Choisir un produit qui a du stock (quantité > 2)
        produits_dispo = [p for p in produits if any(l.produit == p and l.quantite > 2 for l in lots_created)]
        if not produits_dispo:
            continue
            
        produit = random.choice(produits_dispo)
        quantite = random.randint(5, 20)
        prix = float(produit.prix_unitaire) if produit.prix_unitaire else 5000
        
        LigneVente.objects.create(
            vente=vente,
            produit=produit,
            quantite_vendue=quantite,
            prix_unitaire=prix
        )
    
    # Recalculer les montants
    vente.calculer_montants()
    ventes_created.append(vente)
    print(f"   ✅ Vente #{i+1} - {vente.nom_client:30s} - {vente.statut_vente:20s} - {vente.montant_total:,.0f} FCFA")

print(f"\n✅ {len(ventes_created)} ventes créées")

# ============================================================================
# 4. CRÉATION DES LIVRAISONS (avec quantités manquantes)
# ============================================================================
print("\n" + "=" * 80)
print("🚚 CRÉATION DES LIVRAISONS")
print("=" * 80)

livraisons_created = []
# Copie des ventes pour OneToOneField
ventes_disponibles = ventes_created.copy()
for i in range(8):
    # Certaines livraisons en retard
    en_retard = i < 3
    date_prevue = today - timedelta(days=random.randint(1, 5)) if en_retard else today + timedelta(days=random.randint(1, 7))
    
    # Choisir une vente unique (OneToOneField)
    vente_pour_livraison = None
    if ventes_disponibles and random.random() > 0.3:
        vente_pour_livraison = ventes_disponibles.pop(0)
    
    livraison = Livraison.objects.create(
        numero_suivi=f"LIV-{today.strftime('%Y%m')}-{i+1:03d}",
        date_planifiee=date_prevue,
        date_livraison=today - timedelta(days=1) if i < 2 and random.random() > 0.5 else None,
        statut_livraison=random.choice(['planifiée', 'en_cours', 'livrée']) if not en_retard else 'en_cours',
        vente=vente_pour_livraison,
        responsable=gestionnaire_log,
        destination=random.choice([
            "Douala - Centre Ville", "Yaoundé - Bastos", "Kribi - Port",
            "Limbe - Zone Industrielle"
        ]),
        chauffeur_nom=random.choice(["Paul Mbarga", "Jean Nkolo", "Marie Ebelle"]),
        notes="Livraison en retard" if en_retard else "Livraison planifiée"
    )
    
    # Ajouter des lignes avec quantités manquantes
    nb_lignes = random.randint(1, 3)
    for j in range(nb_lignes):
        produit = random.choice(produits)
        qte = random.randint(20, 100)
        
        LivraisonLigne.objects.create(
            livraison=livraison,
            produit=produit,
            quantite=qte
        )
    
    livraisons_created.append(livraison)
    status_icon = "🔴" if en_retard else ("🟢" if livraison.statut_livraison == 'livrée' else "🟡")
    print(f"   {status_icon} Livraison #{i+1} - {livraison.destination:30s} - {livraison.statut_livraison:10s}")

print(f"\n✅ {len(livraisons_created)} livraisons créées")

# ============================================================================
# 5. CRÉATION DES MOUVEMENTS DE STOCK
# ============================================================================
print("\n" + "=" * 80)
print("📊 CRÉATION DES MOUVEMENTS DE STOCK")
print("=" * 80)

mouvements_created = []
for i in range(20):
    lot = random.choice([l for l in lots_created if l.quantite > 2])
    type_mvt = random.choice(['entree', 'sortie', 'ajustement'])
    
    if type_mvt == 'sortie' and lot.quantite < 10:
        type_mvt = 'entree'  # Éviter les sorties sur stock très faible
    
    quantite = random.randint(1, min(20, lot.quantite)) if type_mvt == 'sortie' else random.randint(5, 30)
    
    mouvement = MouvementStock.objects.create(
        lot=lot,
        type_mouvement=type_mvt,
        quantite=quantite,
        date_mouvement=today - timedelta(days=random.randint(0, 20)),
        utilisateur=gestionnaire_stock
    )
    mouvements_created.append(mouvement)

print(f"   ✅ {len(mouvements_created)} mouvements créés")

# ============================================================================
# 6. CRÉATION DES ALERTES
# ============================================================================
print("\n" + "=" * 80)
print("⚠️  CRÉATION DES ALERTES")
print("=" * 80)

alertes_created = []

# Alertes péremption imminente
lots_perimes = [l for l in lots_created if l.date_peremption and (l.date_peremption - today).days <= 5 and l.quantite > 0]
for lot in lots_perimes:
    jours = (lot.date_peremption - today).days
    alerte = Alerte.objects.create(
        type_alerte='peremption',
        niveau=3 if jours <= 2 else 2,
        lot=lot,
        message=f"Péremption imminente: {lot.produit.nom_produit} expire dans {jours} jours",
        date_creation=today
    )
    alertes_created.append(alerte)
    print(f"   🔴 Péremption: {lot.produit.nom_produit} - {jours} jours")

# Alertes rupture stock (quantité <= 1)
lots_rupture = [l for l in lots_created if l.quantite <= 1 and l.produit]
for lot in lots_rupture[:5]:  # Limiter à 5
    try:
        alerte = Alerte.objects.create(
            type_alerte='rupture',
            niveau=3,
            lot=lot,
            message=f"Rupture de stock: {lot.produit.nom_produit} (quantité critique: {lot.quantite})",
            date_creation=today
        )
        alertes_created.append(alerte)
        print(f"   🔴 Rupture: {lot.produit.nom_produit} - {lot.quantite} unité(s)")
    except Exception as e:
        print(f"   ⚠️  Erreur création alerte rupture pour {lot.produit.nom_produit}: {e}")

# Alertes stock faible (2-20 unités)
lots_faibles = [l for l in lots_created if 2 <= l.quantite <= 20 and l.produit]
for lot in lots_faibles[:5]:  # Limiter à 5
    try:
        alerte = Alerte.objects.create(
            type_alerte='seuil',
            niveau=2,
            lot=lot,
            message=f"Stock faible: {lot.produit.nom_produit} ({lot.quantite} unités)",
            date_creation=today
        )
        alertes_created.append(alerte)
        print(f"   🟡 Stock faible: {lot.produit.nom_produit} - {lot.quantite} unités")
    except Exception as e:
        print(f"   ⚠️  Erreur création alerte stock faible pour {lot.produit.nom_produit}: {e}")

print(f"\n✅ {len(alertes_created)} alertes créées")

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
print("\n" + "=" * 80)
print("📊 RÉSUMÉ DU MODE DÉMO")
print("=" * 80)
print(f"""
✅ Lots créés:                {len(lots_created)}
   - Rupture (stock <= 1):     {len([l for l in lots_created if l.quantite <= 1])}
   - Stock faible (2-20):      {len([l for l in lots_created if 2 <= l.quantite <= 20])}
   - Péremption proche (<5j):  {len(lots_perimes)}
   - Stock normal:             {len([l for l in lots_created if l.quantite > 20])}

✅ Approvisionnements:         {len(approvs_created)}
✅ Ventes:                     {len(ventes_created)}
✅ Livraisons:                 {len(livraisons_created)}
   - En retard:                {len([l for l in livraisons_created if l.date_planifiee and l.date_planifiee < today and l.statut_livraison != 'livrée'])}

✅ Mouvements stock:           {len(mouvements_created)}
✅ Alertes:                    {len(alertes_created)}
""")

print("=" * 80)
print("🎉 MODE DÉMO COMPLET CRÉÉ AVEC SUCCÈS!")
print("=" * 80)
