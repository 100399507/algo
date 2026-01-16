import streamlit as st
import copy
import pandas as pd
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products

# ---------------------------------------------
# INITIALISATION DES VARIABLES DE SESSION
# ---------------------------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# ---------------------------------------------
# FONCTIONS
# ---------------------------------------------
def add_buyer(name, auto_bid, product_inputs):
    """Ajoute un acheteur avec ses informations"""
    new_buyer = {"name": name, "auto_bid": auto_bid, "products": {}}
    for prod in products:
        pid = prod["id"]
        data = product_inputs[pid]
        new_buyer["products"][pid] = {
            "current_price": data["price"],
            "max_price": data["max_price"],
            "qty_desired": data["qty_desired"],
        }
    st.session_state.buyers.append(new_buyer)

def update_allocations():
    """Calcul des allocations et mise à jour de l'historique"""
    if st.session_state.buyers:
        # Auto-bid agressif
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        allocations, _ = solve_model(st.session_state.buyers, products)

        # Sauvegarde dans l'historique
        hist_record = {}
        for buyer in st.session_state.buyers:
            hist_record[buyer["name"]] = {}
            for pid, pdata in buyer["products"].items():
                hist_record[buyer["name"]][pid] = {
                    "allocated": allocations[buyer["name"]][pid],
                    "current_price": pdata["current_price"],
                    "max_price": pdata["max_price"],
                    "qty_desired": pdata["qty_desired"],
                }
        st.session_state.history.append(hist_record)
        return allocations
    return {}

# ---------------------------------------------
# INTERFACE
# ---------------------------------------------
st.title("💰 Simulateur d'enchères")
st.markdown("### Informations produits de départ")
prod_data = pd.DataFrame([{
    "Produit": p["name"],
    "Stock": p["stock"],
    "Multiple": p["volume_multiple"],
    "Prix départ": p["starting_price"]
} for p in products])
st.table(prod_data)

st.markdown("---")
st.subheader("Ajouter ou modifier un acheteur")

# Formulaire pour saisir/modifier un acheteur
with st.form("buyer_form"):
    buyer_name = st.text_input("Nom de l'acheteur", f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Auto-bid activé ?", value=True)

    product_inputs = {}
    for p in products:
        pid = p["id"]
        st.markdown(f"**{p['name']}**")
        cols = st.columns(3)
        price = cols[0].number_input(f"Prix offert ({pid})", min_value=0.0, value=p["starting_price"] + 0.5, step=0.1)
        max_price = cols[1].number_input(f"Prix max ({pid})", min_value=price, value=price+5.0, step=0.1)
        qty_desired = cols[2].number_input(f"Qté désirée ({pid})", min_value=1, value=min(100, p["stock"]//3), step=p["volume_multiple"])
        product_inputs[pid] = {"price": price, "max_price": max_price, "qty_desired": qty_desired}

    submitted = st.form_submit_button("Ajouter / Modifier acheteur")
    if submitted:
        # Vérifier si acheteur existant
        existing = next((b for b in st.session_state.buyers if b["name"] == buyer_name), None)
        if existing:
            # Mise à jour
            for pid, pdata in product_inputs.items():
                existing["products"][pid]["current_price"] = pdata["price"]
                existing["products"][pid]["max_price"] = pdata["max_price"]
                existing["products"][pid]["qty_desired"] = pdata["qty_desired"]
            existing["auto_bid"] = auto_bid
        else:
            add_buyer(buyer_name, auto_bid, product_inputs)

        allocations = update_allocations()
        st.success("✅ Allocation recalculée")

# ---------------------------------------------
# AFFICHAGE DES ALLOCATIONS COURANTES
# ---------------------------------------------
if st.session_state.buyers:
    st.markdown("---")
    st.subheader("📊 Allocations courantes")

    current_rows = []
    allocations, _ = solve_model(st.session_state.buyers, products)
    for buyer in st.session_state.buyers:
        row = {"Acheteur": buyer["name"]}
        for pid, pdata in buyer["products"].items():
            row[f"{pid} (Alloué)"] = allocations[buyer["name"]][pid]
            row[f"{pid} (Prix offert)"] = pdata["current_price"]
            row[f"{pid} (Prix max)"] = pdata["max_price"]
            row[f"{pid} (Qté désirée)"] = pdata["qty_desired"]
        current_rows.append(row)
    st.dataframe(pd.DataFrame(current_rows), use_container_width=True)

# ---------------------------------------------
# HISTORIQUE
# ---------------------------------------------
if st.session_state.history:
    st.markdown("---")
    st.subheader("📜 Historique des allocations")
    for i, record in enumerate(st.session_state.history, 1):
        st.markdown(f"**Itération {i}**")
        hist_rows = []
        for b in st.session_state.buyers:
            buyer_name = b["name"]
            if buyer_name not in record:
                continue
            allocs = record[buyer_name]
            row = {"Acheteur": buyer_name}
            for pid, pdata in allocs.items():
                row[f"{pid} (Alloué)"] = pdata.get("allocated", "")
                row[f"{pid} (Prix utilisé)"] = pdata.get("current_price", "")
                row[f"{pid} (Prix max)"] = pdata.get("max_price", "")
                row[f"{pid} (Qté désirée)"] = pdata.get("qty_desired", "")
            hist_rows.append(row)
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
