# app.py
import streamlit as st
import pandas as pd
import copy
from allocation_algo import solve_model
from products_config import products, SELLER_GLOBAL_MOQ

# -----------------------------
# Initialisation session_state
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Cadre produits de départ
# -----------------------------
st.title("💻 Simulateur d'Enchères")
st.subheader("📦 Informations produits")
prod_data = []
for p in products:
    prod_data.append({
        "Produit": p["name"],
        "Stock initial": p["stock"],
        "MOQ vendeur": p["seller_moq"],
        "Multiple": p["volume_multiple"],
        "Prix départ": p["starting_price"]
    })
st.table(pd.DataFrame(prod_data))

st.markdown("---")

# -----------------------------
# Ajouter un nouvel acheteur
# -----------------------------
st.subheader("➕ Ajouter / Modifier un acheteur")
with st.form("new_buyer_form"):
    name = st.text_input("Nom de l'acheteur", f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Auto-bid activé ?", value=True)

    buyer_inputs = {}
    for p in products:
        st.markdown(f"**{p['name']} ({p['id']})**")
        col1, col2, col3 = st.columns(3)
        with col1:
            qty_desired = st.number_input(
                "Quantité souhaitée",
                min_value=p["seller_moq"],
                max_value=p["stock"],
                value=min(50, p["stock"]),
                step=p["volume_multiple"],
                key=f"{name}_{p['id']}_qty"
            )
        with col2:
            moq = st.number_input(
                "MOQ",
                min_value=p["seller_moq"],
                max_value=qty_desired,
                value=min(30, qty_desired),
                step=p["volume_multiple"],
                key=f"{name}_{p['id']}_moq"
            )
        with col3:
            price_current = st.number_input(
                "Prix offert",
                min_value=p["starting_price"],
                value=p["starting_price"] + 0.5,
                step=0.1,
                key=f"{name}_{p['id']}_price"
            )
            price_max = st.number_input(
                "Prix max",
                min_value=price_current,
                value=price_current + 5.0,
                step=0.1,
                key=f"{name}_{p['id']}_max"
            )

        buyer_inputs[p["id"]] = {
            "qty_desired": qty_desired,
            "moq": moq,
            "current_price": price_current,
            "max_price": price_max
        }

    submitted = st.form_submit_button("Ajouter / Mettre à jour")

if submitted:
    # Vérifie si l'acheteur existe déjà
    exists = False
    for i, b in enumerate(st.session_state.buyers):
        if b["name"] == name:
            st.session_state.buyers[i]["products"] = buyer_inputs
            st.session_state.buyers[i]["auto_bid"] = auto_bid
            exists = True
            st.success(f"Acheteur {name} mis à jour !")
            break

    if not exists:
        st.session_state.buyers.append({
            "name": name,
            "auto_bid": auto_bid,
            "products": buyer_inputs
        })
        st.success(f"Acheteur {name} ajouté !")

    # Recalcul allocations
    allocations, total_ca = solve_model(st.session_state.buyers, products)

    # Enregistrer l'historique complet
    hist_record = {}
    for b in st.session_state.buyers:
        buyer_data = {}
        for pid, prod in b["products"].items():
            buyer_data[pid] = {
                "qty_desired": prod.get("qty_desired", 0),
                "moq": prod.get("moq", 0),
                "current_price": prod.get("current_price", 0),
                "max_price": prod.get("max_price", 0),
                "allocated": allocations[b["name"]][pid]
            }
        hist_record[b["name"]] = buyer_data
    st.session_state.history.append(hist_record)

# -----------------------------
# Afficher allocations actuelles
# -----------------------------
if st.session_state.buyers:
    st.subheader("📊 Allocations actuelles")
    rows = []
    for b in st.session_state.buyers:
        row = {"Acheteur": b["name"]}
        for p in products:
            pid = p["id"]
            prod_data = b["products"][pid]
            row[f"{pid} (Quantité souhaitée)"] = prod_data["qty_desired"]
            row[f"{pid} (MOQ)"] = prod_data["moq"]
            row[f"{pid} (Prix offert)"] = prod_data["current_price"]
            row[f"{pid} (Prix max)"] = prod_data["max_price"]
            row[f"{pid} (Alloué)"] = allocations[b["name"]][pid]
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.markdown(f"**CA total:** {total_ca:.2f}€")
    st.markdown(f"⚠️ MOQ global vendeur = {SELLER_GLOBAL_MOQ}")

# -----------------------------
# Historique complet
# -----------------------------
if st.session_state.history:
    st.subheader("📜 Historique des allocations")
    for i, record in enumerate(st.session_state.history, 1):
        st.markdown(f"**Itération {i}**")
        hist_rows = []
        for b in st.session_state.buyers:
            buyer_name = b["name"]
            row = {"Acheteur": buyer_name}
            buyer_record = record.get(buyer_name, {})
            for p in products:
                pid = p["id"]
                prod_record = buyer_record.get(pid, {})
                row[f"{pid} (Quantité souhaitée)"] = prod_record.get("qty_desired", "")
                row[f"{pid} (MOQ)"] = prod_record.get("moq", "")
                row[f"{pid} (Prix offert)"] = prod_record.get("current_price", "")
                row[f"{pid} (Prix max)"] = prod_record.get("max_price", "")
                row[f"{pid} (Alloué)"] = prod_record.get("allocated", "")
            hist_rows.append(row)
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
