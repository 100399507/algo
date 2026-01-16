import streamlit as st
import pandas as pd
from allocation_algo import solve_model
from products_config import products, SELLER_GLOBAL_MOQ
import copy

st.set_page_config(page_title="Simulateur d'Enchères", layout="wide")

# -----------------------------
# Session state initialisation
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Affichage informations produits
# -----------------------------
st.sidebar.header("🛒 Informations produits de départ")
for p in products:
    st.sidebar.markdown(
        f"**{p['name']} ({p['id']})**\n"
        f"Stock: {p['stock']} | MOQ vendeur: {p['seller_moq']} | Multiple: {p['volume_multiple']} | "
        f"Prix départ: {p['starting_price']}€"
    )

st.title("💰 Simulateur d'Enchères Séquentiel")

# -----------------------------
# Ajouter un nouvel acheteur
# -----------------------------
st.subheader("➕ Ajouter un nouvel acheteur")
with st.form("add_buyer_form"):
    buyer_name = st.text_input("Nom de l'acheteur", value=f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Auto-bid activé ?", value=True)
    new_buyer = {
        "name": buyer_name,
        "auto_bid": auto_bid,
        "products": {}
    }

    for pid, p in enumerate(products):
        st.markdown(f"**Produit {p['name']} ({p['id']})**")
        col1, col2, col3 = st.columns(3)
        with col1:
            qty = st.number_input(
                f"Quantité désirée ({p['id']})",
                min_value=p['seller_moq'],
                max_value=p['stock'],
                step=p['volume_multiple'],
                value=min(50, p['stock']//3),
                key=f"qty_{len(st.session_state.buyers)}_{pid}"
            )
        with col2:
            moq = st.number_input(
                f"MOQ ({p['id']})",
                min_value=1,
                max_value=qty,
                step=p['volume_multiple'],
                value=min(30, qty//2),
                key=f"moq_{len(st.session_state.buyers)}_{pid}"
            )
        with col3:
            price = st.number_input(
                f"Prix actuel ({p['id']})",
                min_value=p['starting_price'],
                value=p['starting_price'] + 0.5,
                step=0.05,
                key=f"price_{len(st.session_state.buyers)}_{pid}"
            )
            max_price = st.number_input(
                f"Prix max ({p['id']})",
                min_value=price,
                value=price + 5.0,
                step=0.05,
                key=f"max_{len(st.session_state.buyers)}_{pid}"
            )

        new_buyer["products"][p["id"]] = {
            "qty_desired": qty,
            "moq": moq,
            "current_price": price,
            "max_price": max_price
        }

    submitted = st.form_submit_button("Ajouter l'acheteur")
    if submitted:
        st.session_state.buyers.append(new_buyer)
        st.success(f"Acheteur {buyer_name} ajouté !")

        # -----------------------------
        # Calcul allocations
        # -----------------------------
        st.session_state.history.append(copy.deepcopy({
            b["name"]: {pid: b["products"][pid]["current_price"] for pid in b["products"]}
            for b in st.session_state.buyers
        }))

# -----------------------------
# Modifier le prix d'un acheteur existant
# -----------------------------
st.subheader("✏️ Modifier prix d'un acheteur")
if st.session_state.buyers:
    buyer_names = [b["name"] for b in st.session_state.buyers]
    selected_buyer_idx = st.selectbox("Sélectionner un acheteur", range(len(buyer_names)), format_func=lambda x: buyer_names[x])
    selected_buyer = st.session_state.buyers[selected_buyer_idx]

    with st.form("modify_price_form"):
        for pid, prod in enumerate(products):
            prod_id = prod["id"]
            st.markdown(f"**Produit {prod['name']} ({prod_id})**")
            col1, col2 = st.columns(2)
            with col1:
                new_price = st.number_input(
                    f"Prix actuel ({prod_id})",
                    min_value=prod['starting_price'],
                    max_value=selected_buyer["products"][prod_id]["max_price"],
                    value=selected_buyer["products"][prod_id]["current_price"],
                    step=0.05,
                    key=f"mod_price_{selected_buyer_idx}_{pid}"
                )
            with col2:
                new_max_price = st.number_input(
                    f"Prix max ({prod_id})",
                    min_value=new_price,
                    value=selected_buyer["products"][prod_id]["max_price"],
                    step=0.05,
                    key=f"mod_max_{selected_buyer_idx}_{pid}"
                )
            selected_buyer["products"][prod_id]["current_price"] = new_price
            selected_buyer["products"][prod_id]["max_price"] = new_max_price

        submitted_mod = st.form_submit_button("Mettre à jour prix et recalculer")
        if submitted_mod:
            st.success("Prix mis à jour. Recalcul des allocations...")
            # Sauvegarder l'état actuel pour l'historique
            st.session_state.history.append(copy.deepcopy({
                b["name"]: {pid: b["products"][pid]["current_price"] for pid in b["products"]}
                for b in st.session_state.buyers
            }))

# -----------------------------
# Affichage allocations et historique
# -----------------------------
if st.session_state.buyers:
    st.subheader("📊 Allocations actuelles")
    allocations, total_ca = solve_model(st.session_state.buyers, products)

    alloc_rows = []
    for b in st.session_state.buyers:
        row = {"Acheteur": b["name"]}
        for pid, p in enumerate(products):
            prod_id = p["id"]
            row[f"{prod_id} (Alloué)"] = allocations[b["name"]][prod_id]
            row[f"{prod_id} (Prix actuel)"] = b["products"][prod_id]["current_price"]
            row[f"{prod_id} (Prix max)"] = b["products"][prod_id]["max_price"]
            row[f"{prod_id} (Quantité souhaitée)"] = b["products"][prod_id]["qty_desired"]
            row[f"{prod_id} (MOQ)"] = b["products"][prod_id]["moq"]
        alloc_rows.append(row)
    st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True)

    st.markdown(f"**CA total : {total_ca:.2f}€**")

# -----------------------------
# Historique
# -----------------------------
if st.session_state.history:
    st.subheader("📜 Historique des prix")
    for i, record in enumerate(st.session_state.history, 1):
        st.markdown(f"**Itération {i}**")
        hist_rows = []
        for b in st.session_state.buyers:
            row = {"Acheteur": b["name"]}
            for pid, p in enumerate(products):
                prod_id = p["id"]
                row[f"{prod_id} (Prix utilisé)"] = record[b["name"]][prod_id]
            hist_rows.append(row)
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
