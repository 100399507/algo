import streamlit as st
import pandas as pd
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ

# -----------------------------
# Initialisation du state
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Cadre produits de départ
# -----------------------------
st.title("💰 Simulateur d'enchères B2B")
st.header("📦 Informations produits de départ")
prod_info = pd.DataFrame([
    {
        "Produit": p["name"],
        "Stock": p["stock"],
        "MOQ vendeur": p.get("seller_moq", 0),
        "Multiple": p["volume_multiple"],
        "Prix départ": p["starting_price"]
    } for p in products
])
st.table(prod_info)

# -----------------------------
# Formulaire ajout d’un acheteur
# -----------------------------
st.subheader("➕ Ajouter un nouvel acheteur")
with st.form("add_buyer_form"):
    buyer_name = st.text_input("Nom de l'acheteur", f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Auto-bid activé ?", value=True)

    buyer_products = {}
    for product in products:
        prod_id = product["id"]
        col1, col2, col3, col4 = st.columns(4)

        # Quantité désirée
        qty_default = min(100, product['stock']//3)
        qty_default = max(product["volume_multiple"], (qty_default // product["volume_multiple"]) * product["volume_multiple"])
        qty_desired = col1.number_input(
            f"Qté désirée {product['name']}",
            min_value=product["volume_multiple"],
            max_value=product['stock'],
            value=qty_default,
            step=product["volume_multiple"],
            key=f"{buyer_name}_{prod_id}_qty"
        )

        # MOQ
        moq_default = max(product["volume_multiple"], qty_desired//2)
        moq = col2.number_input(
            f"MOQ {product['name']}",
            min_value=product["volume_multiple"],
            max_value=qty_desired,
            value=moq_default,
            step=product["volume_multiple"],
            key=f"{buyer_name}_{prod_id}_moq"
        )

        # Prix offert et prix max
        current_price = col3.number_input(
            f"Prix offert {product['name']}",
            min_value=float(product['starting_price']),
            value=float(product['starting_price'] + 0.5),
            step=0.1,
            key=f"{buyer_name}_{prod_id}_price"
        )
        max_price = col4.number_input(
            f"Prix max {product['name']}",
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
        # Recalcul allocations
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        allocations, _ = solve_model(st.session_state.buyers, products)
        st.session_state.history.append({b["name"]: allocations[b["name"]] for b in st.session_state.buyers})
        st.success(f"{buyer_name} ajouté et allocations recalculées !")

# -----------------------------
# Modifier le prix max d’un acheteur
# -----------------------------
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
            # Recalcul allocations
            st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
            allocations, _ = solve_model(st.session_state.buyers, products)
            st.session_state.history.append({b["name"]: allocations[b["name"]] for b in st.session_state.buyers})
            st.success(f"✅ Prix max de {buyer_data['name']} mis à jour et allocations recalculées !")

# -----------------------------
# Tableau allocations actuelles
# -----------------------------
st.subheader("📊 État actuel des allocations")
if st.session_state.buyers:
    allocations, _ = solve_model(st.session_state.buyers, products)
    rows = []
    for buyer in st.session_state.buyers:
        row = {"Acheteur": buyer["name"], "Auto-bid": "✅" if buyer.get("auto_bid") else "❌"}
        for product in products:
            pid = product["id"]
            row[f"{pid} Qté désirée"] = buyer["products"][pid]["qty_desired"]
            row[f"{pid} MOQ"] = buyer["products"][pid]["moq"]
            row[f"{pid} Prix offert"] = buyer["products"][pid]["current_price"]
            row[f"{pid} Prix max"] = buyer["products"][pid]["max_price"]
            row[f"{pid} Alloué"] = allocations[buyer["name"]][pid]
        rows.append(row)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Aucun acheteur pour l'instant")

# -----------------------------
# Historique complet
# -----------------------------
st.subheader("🕒 Historique des allocations")
for i, record in enumerate(st.session_state.history, 1):
    st.markdown(f"**Itération {i}**")
    hist_rows = []
    for buyer in st.session_state.buyers:
        buyer_name = buyer["name"]
        allocs = record[buyer_name]
        row = {"Acheteur": buyer_name}
        for product in products:
            pid = product["id"]
            row[f"{pid} Qté désirée"] = buyer["products"][pid]["qty_desired"]
            row[f"{pid} MOQ"] = buyer["products"][pid]["moq"]
            row[f"{pid} Prix offert"] = buyer["products"][pid]["current_price"]
            row[f"{pid} Prix max"] = buyer["products"][pid]["max_price"]
            row[f"{pid} Alloué"] = allocs[pid]
        hist_rows.append(row)
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)
