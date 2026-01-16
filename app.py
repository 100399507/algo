import streamlit as st
import pandas as pd
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ
import math

# -----------------------------
# Fonctions utiles
# -----------------------------
def round_to_multiple(value, multiple):
    if multiple <= 0:
        return value
    return int(round(value / multiple) * multiple)

def initialize_session_state():
    if "buyers" not in st.session_state:
        st.session_state.buyers = []
    if "history" not in st.session_state:
        st.session_state.history = []

def display_products_info(products):
    st.info(
        "\n".join(
            [f"{p['name']} (Stock: {p['stock']}, Multiple: {p['volume_multiple']}, Prix départ: {p['starting_price']:.2f}€)" for p in products]
        ),
        icon="📦"
    )

def add_buyer_form(products):
    st.subheader("➕ Ajouter un nouvel acheteur")
    with st.form("add_buyer_form"):
        buyer_name = st.text_input("Nom de l'acheteur", f"Acheteur_{len(st.session_state.buyers)+1}")
        auto_bid = st.checkbox("Auto-bid activé ?", value=True)

        buyer_products = {}
        for product in products:
            prod_id = product["id"]
            col1, col2, col3 = st.columns(3)
            with col1:
                qty_desired = st.number_input(
                    f"Quantité désirée - {product['name']}",
                    min_value=product["volume_multiple"],
                    value=min(100, product['stock']//3),
                    step=product['volume_multiple'],
                    key=f"{buyer_name}_{prod_id}_qty"
                )
            with col2:
                moq = st.number_input(
                    f"MOQ - {product['name']}",
                    min_value=product["volume_multiple"],
                    value=min(30, qty_desired//2),
                    step=product['volume_multiple'],
                    key=f"{buyer_name}_{prod_id}_moq"
                )
            with col3:
                current_price = st.number_input(
                    f"Prix offert - {product['name']}",
                    min_value=product["starting_price"],
                    value=product["starting_price"] + 0.5,
                    step=0.1,
                    key=f"{buyer_name}_{prod_id}_price"
                )
                max_price = st.number_input(
                    f"Prix max - {product['name']}",
                    min_value=current_price,
                    value=current_price + 5.0,
                    step=0.1,
                    key=f"{buyer_name}_{prod_id}_max_price"
                )

            buyer_products[prod_id] = {
                "qty_desired": qty_desired,
                "moq": moq,
                "current_price": current_price,
                "max_price": max_price
            }

        submitted = st.form_submit_button("Ajouter acheteur et recalculer allocations")
        if submitted:
            new_buyer = {
                "name": buyer_name,
                "auto_bid": auto_bid,
                "products": buyer_products
            }
            st.session_state.buyers.append(new_buyer)
            # Auto-bid agressif pour mise à jour des allocations
            st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
            allocations, _ = solve_model(st.session_state.buyers, products)
            st.session_state.history.append({b["name"]: allocations[b["name"]] for b in st.session_state.buyers})
            st.success(f"{buyer_name} ajouté et allocations recalculées !")

def display_allocations(products):
    st.subheader("📊 État actuel des allocations")
    if not st.session_state.buyers:
        st.info("Aucun acheteur pour l'instant")
        return

    allocations, total_ca = solve_model(st.session_state.buyers, products)
    st.write(f"**CA total : {total_ca:.2f}€**")

    rows = []
    for buyer in st.session_state.buyers:
        row = {"Acheteur": buyer["name"], "Auto-bid": "✅" if buyer.get("auto_bid") else "❌"}
        for product in products:
            pid = product["id"]
            alloc = allocations[buyer["name"]][pid]
            row[f"{pid} (Alloué)"] = alloc
            row[f"{pid} (Prix)"] = buyer["products"][pid]["current_price"]
        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

def display_history():
    st.subheader("🕒 Historique des allocations")
    if not st.session_state.history:
        st.info("Aucune itération historique")
        return
    for i, record in enumerate(st.session_state.history, 1):
        st.markdown(f"**Itération {i}**")
        hist_rows = []
        for buyer_name, allocs in record.items():
            row = {"Acheteur": buyer_name}
            for pid, qty in allocs.items():
                # Chercher le prix correspondant
                buyer = next(b for b in st.session_state.buyers if b["name"] == buyer_name)
                row[f"{pid} (Alloué)"] = qty
                row[f"{pid} (Prix)"] = buyer["products"][pid]["current_price"]
            hist_rows.append(row)
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)

def modify_max_price():
    if st.session_state.buyers:
        st.subheader("⚙️ Modifier le Prix max d'un acheteur existant")
        buyer_names = [b["name"] for b in st.session_state.buyers]
        selected_buyer = st.selectbox("Sélectionnez un acheteur", [""] + buyer_names)
        if selected_buyer:
            buyer_idx = buyer_names.index(selected_buyer)
            buyer_data = st.session_state.buyers[buyer_idx]
            updated_prices = {}
            for product in products:
                pid = product["id"]
                updated_prices[pid] = st.number_input(
                    f"Prix max {product['name']} - {buyer_data['name']}",
                    min_value=buyer_data["products"][pid]["current_price"],
                    value=buyer_data["products"][pid]["max_price"],
                    step=0.1,
                    key=f"update_max_{buyer_data['name']}_{pid}"
                )
            if st.button("🔄 Mettre à jour prix max et recalculer allocations"):
                for pid in updated_prices:
                    buyer_data["products"][pid]["max_price"] = updated_prices[pid]
                st.session_state.buyers[buyer_idx] = buyer_data
                st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
                allocations, _ = solve_model(st.session_state.buyers, products)
                st.session_state.history.append({b["name"]: allocations[b["name"]] for b in st.session_state.buyers})
                st.success(f"✅ Prix max de {buyer_data['name']} mis à jour et allocations recalculées !")

# -----------------------------
# Main
# -----------------------------
st.title("💰 Simulateur d'enchères séquentiel")
initialize_session_state()

# Cadre informations produits
st.header("📦 Informations produits de départ")
display_products_info(products)

# Formulaire ajout acheteur
add_buyer_form(products)

# Modifier le prix max
modify_max_price()

# État actuel
display_allocations(products)

# Historique
display_history()
