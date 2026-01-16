import streamlit as st
import pandas as pd
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products

# -----------------------------
# Initialisation
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Affichage info produits
# -----------------------------
st.title("🏷️ Simulateur d'enchères séquentiel")
st.subheader("Informations produits de départ")
prod_data = []
for p in products:
    prod_data.append({
        "Produit": p["name"],
        "Stock": p["stock"],
        "Prix départ": p["starting_price"],
        "Multiple": p["volume_multiple"]
    })
st.table(pd.DataFrame(prod_data))

# -----------------------------
# Ajouter / Modifier Acheteur
# -----------------------------
st.sidebar.header("Ajouter / Modifier Acheteur")
buyer_names = [b["name"] for b in st.session_state.buyers]

action = st.sidebar.selectbox("Action", ["Ajouter nouvel acheteur", "Modifier un acheteur existant"])

if action == "Ajouter nouvel acheteur":
    new_name = st.sidebar.text_input("Nom de l'acheteur", f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.sidebar.checkbox("Auto-bid activé ?", value=True)

    new_products = {}
    for p in products:
        st.sidebar.subheader(p["name"])
        default_price = p["starting_price"] + 0.5
        current_price = st.sidebar.number_input(f"Prix offert ({p['name']})", min_value=p["starting_price"], value=float(default_price), step=0.05)
        max_price = st.sidebar.number_input(f"Prix max ({p['name']})", min_value=current_price, value=float(current_price + 5), step=0.05)
        qty_desired = st.sidebar.number_input(f"Quantité désirée ({p['name']})", min_value=1, value=min(100, p["stock"]//3), step=p["volume_multiple"])
        moq = st.sidebar.number_input(f"MOQ ({p['name']})", min_value=1, value=min(30, qty_desired//2), step=p["volume_multiple"])

        new_products[p["id"]] = {
            "current_price": current_price,
            "max_price": max_price,
            "qty_desired": qty_desired,
            "moq": moq
        }

    if st.sidebar.button("Ajouter acheteur"):
        st.session_state.buyers.append({
            "name": new_name,
            "auto_bid": auto_bid,
            "products": new_products
        })

        # Auto-bid agressif
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)

        # Calcul allocations et mise à jour prix réel
        allocations, total_ca = solve_model(st.session_state.buyers, products)
        for b in st.session_state.buyers:
            for pid, prod in b["products"].items():
                prod["current_price"] = prod.get("current_price", prod["current_price"])

        # Historique complet
        hist_record = {}
        for b in st.session_state.buyers:
            buyer_data = {}
            for pid, prod in b["products"].items():
                buyer_data[pid] = {
                    "qty_desired": prod.get("qty_desired", 0),
                    "current_price": prod.get("current_price", 0),
                    "max_price": prod.get("max_price", 0),
                    "allocated": allocations[b["name"]][pid]
                }
            hist_record[b["name"]] = buyer_data
        st.session_state.history.append(hist_record)

elif action == "Modifier un acheteur existant" and st.session_state.buyers:
    selected_buyer = st.sidebar.selectbox("Choisir acheteur", buyer_names)
    buyer = next(b for b in st.session_state.buyers if b["name"] == selected_buyer)

    for p in products:
        st.sidebar.subheader(p["name"])
        new_price = st.sidebar.number_input(f"Modifier prix offert ({p['name']})", min_value=p["starting_price"], value=buyer["products"][p["id"]]["current_price"], step=0.05)
        new_max = st.sidebar.number_input(f"Modifier prix max ({p['name']})", min_value=new_price, value=buyer["products"][p["id"]]["max_price"], step=0.05)
        buyer["products"][p["id"]]["current_price"] = new_price
        buyer["products"][p["id"]]["max_price"] = new_max

    if st.sidebar.button("Recalculer allocations"):
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        allocations, total_ca = solve_model(st.session_state.buyers, products)
        for b in st.session_state.buyers:
            for pid, prod in b["products"].items():
                prod["current_price"] = prod.get("current_price", prod["current_price"])

        # Historique
        hist_record = {}
        for b in st.session_state.buyers:
            buyer_data = {}
            for pid, prod in b["products"].items():
                buyer_data[pid] = {
                    "qty_desired": prod.get("qty_desired", 0),
                    "current_price": prod.get("current_price", 0),
                    "max_price": prod.get("max_price", 0),
                    "allocated": allocations[b["name"]][pid]
                }
            hist_record[b["name"]] = buyer_data
        st.session_state.history.append(hist_record)

# -----------------------------
# Affichage allocations actuelles
# -----------------------------
if st.session_state.buyers:
    st.subheader("💰 Allocations actuelles")
    allocations, total_ca = solve_model(st.session_state.buyers, products)
    table_rows = []
    for b in st.session_state.buyers:
        row = {"Acheteur": b["name"]}
        for p in products:
            pid = p["id"]
            row[f"{pid} (Alloué)"] = allocations[b["name"]][pid]
            row[f"{pid} (Prix utilisé)"] = b["products"][pid]["current_price"]
            row[f"{pid} (Prix max)"] = b["products"][pid]["max_price"]
            row[f"{pid} (Qté désirée)"] = b["products"][pid]["qty_desired"]
        table_rows.append(row)
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
    st.markdown(f"**CA total simulé : {total_ca:.2f} €**")

# -----------------------------
# Historique
# -----------------------------
if st.session_state.history:
    st.subheader("📊 Historique des allocations")
    for i, record in enumerate(st.session_state.history, 1):
        st.markdown(f"**Itération {i}**")
        hist_rows = []
        for b in st.session_state.buyers:
            buyer_name = b["name"]
            allocs = record[buyer_name]
            row = {"Acheteur": buyer_name}
            for pid, pdata in allocs.items():
                row[f"{pid} (Alloué)"] = pdata["allocated"]
                row[f"{pid} (Prix utilisé)"] = pdata["current_price"]
                row[f"{pid} (Prix max)"] = pdata["max_price"]
                row[f"{pid} (Qté désirée)"] = pdata["qty_desired"]
            hist_rows.append(row)
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
