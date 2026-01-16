import streamlit as st
import pandas as pd
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ

# Initialisation du state
if 'buyers' not in st.session_state:
    st.session_state.buyers = []

if 'history' not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Affichage informations produits
# -----------------------------
st.title("💰 Simulateur d'enchères")
st.markdown("### Informations produits de départ")
prod_info = pd.DataFrame([
    {
        "Produit": p["name"],
        "Stock": p["stock"],
        "MOQ": p["seller_moq"],
        "Multiple": p["volume_multiple"],
        "Prix départ": p["starting_price"]
    } for p in products
])
st.table(prod_info)

st.markdown("---")

# -----------------------------
# Ajouter ou modifier un acheteur
# -----------------------------
st.subheader("🧑 Ajouter / Modifier un acheteur")

# Choix acheteur
buyer_names = [b["name"] for b in st.session_state.buyers]
selected_buyer = st.selectbox(
    "Sélectionnez un acheteur à modifier ou laissez vide pour en ajouter un nouveau",
    [""] + buyer_names
)

# Valeurs par défaut si nouvel acheteur
new_buyer_defaults = {
    "name": "",
    "auto_bid": True,
    "products": {p["id"]: {
        "current_price": p["starting_price"] + 0.5,
        "max_price": p["starting_price"] + 5.0,
        "qty_desired": min(100, p["stock"] // 3),
        "moq": min(30, p["stock"] // 5)
    } for p in products}
}

# Si un acheteur existant est sélectionné
if selected_buyer:
    buyer_idx = buyer_names.index(selected_buyer)
    buyer_data = st.session_state.buyers[buyer_idx]
else:
    buyer_data = new_buyer_defaults.copy()

# Nom
buyer_data["name"] = st.text_input("Nom de l'acheteur", value=buyer_data["name"])

# Auto-bid
buyer_data["auto_bid"] = st.checkbox("Auto-bid activé ?", value=buyer_data.get("auto_bid", True))

# Produits
for product in products:
    prod_id = product["id"]
    st.markdown(f"**{product['name']} ({prod_id})**")
    col1, col2, col3 = st.columns(3)

    # Prix actuel
    buyer_data["products"][prod_id]["current_price"] = col1.number_input(
        "Prix actuel",
        min_value=product["starting_price"],
        value=float(buyer_data["products"][prod_id]["current_price"]),
        step=0.01,
        key=f"cp_{buyer_data['name']}_{prod_id}"
    )

    # Prix max
    buyer_data["products"][prod_id]["max_price"] = col2.number_input(
        "Prix max",
        min_value=buyer_data["products"][prod_id]["current_price"],
        value=float(buyer_data["products"][prod_id]["max_price"]),
        step=0.01,
        key=f"mp_{buyer_data['name']}_{prod_id}"
    )

    # Quantité désirée (respect du multiple)
    step_val = product["volume_multiple"]
    buyer_data["products"][prod_id]["qty_desired"] = col3.number_input(
        f"Quantité désirée (Multiple {step_val})",
        min_value=buyer_data["products"][prod_id]["moq"],
        value=int(buyer_data["products"][prod_id]["qty_desired"]),
        step=step_val,
        key=f"qty_{buyer_data['name']}_{prod_id}"
    )

    # MOQ (respect du multiple)
    buyer_data["products"][prod_id]["moq"] = col3.number_input(
        f"MOQ (Multiple {step_val})",
        min_value=step_val,
        value=int(buyer_data["products"][prod_id]["moq"]),
        step=step_val,
        key=f"moq_{buyer_data['name']}_{prod_id}"
    )

# Bouton pour sauvegarder / ajouter l’acheteur
if st.button("✅ Sauvegarder / Ajouter cet acheteur"):
    if selected_buyer:
        # Mise à jour d’un acheteur existant
        st.session_state.buyers[buyer_idx] = buyer_data
    else:
        # Nouvel acheteur
        st.session_state.buyers.append(buyer_data)

    # Recalcul allocations avec auto-bid agressif
    st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)

    # Sauvegarde de l’état dans l’historique
    allocations, _ = solve_model(st.session_state.buyers, products)
    st.session_state.history.append({b["name"]: allocations[b["name"]] for b in st.session_state.buyers})

    st.success("✅ Allocation recalculée avec succès !")

# -----------------------------
# Affichage allocations actuelles
# -----------------------------
st.subheader("📈 État actuel des allocations")
if st.session_state.buyers:
    allocations, _ = solve_model(st.session_state.buyers, products)
    hist_rows = []
    for buyer in st.session_state.buyers:
        row = {"Acheteur": buyer["name"]}
        for prod_id in allocations[buyer["name"]]:
            row[f"{prod_id} (Alloué)"] = allocations[buyer["name"]][prod_id]
            row[f"{prod_id} (Prix)"] = buyer["products"][prod_id]["current_price"]
        hist_rows.append(row)
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
else:
    st.info("Aucun acheteur pour l'instant")

# -----------------------------
# Historique complet
# -----------------------------
st.subheader("🕘 Historique des allocations")
for i, record in enumerate(st.session_state.history, 1):
    st.markdown(f"**Itération {i}**")
    hist_rows = []
    for buyer in st.session_state.buyers:
        buyer_name = buyer["name"]
        allocs = record[buyer_name]
        row = {"Acheteur": buyer_name}
        for prod_id in allocs:
            row[f"{prod_id} (Alloué)"] = allocs[prod_id]
            row[f"{prod_id} (Prix)"] = buyer["products"][prod_id]["current_price"]
        hist_rows.append(row)
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
