import streamlit as st
import pandas as pd
import copy

from allocation_algo import (
    solve_model,
    run_auto_bid_aggressive,
)

from products_config import products, SELLER_GLOBAL_MOQ

# -----------------------------------
# Page config
# -----------------------------------
st.set_page_config(
    page_title="Allocation Engine – Test UI",
    layout="wide"
)

# -----------------------------------
# Session state
# -----------------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------------
# Helpers
# -----------------------------------
def snapshot(label):
    allocations, total_ca = solve_model(st.session_state.buyers, products)
    st.session_state.history.append({
        "label": label,
        "buyers": copy.deepcopy(st.session_state.buyers),
        "allocations": allocations,
        "total_ca": total_ca
    })


def buyers_to_df():
    rows = []
    for b in st.session_state.buyers:
        for pid, p in b["products"].items():
            rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Prix courant": p["current_price"],
                "Prix max": p["max_price"],
                "Qté désirée": p["qty_desired"],
                "MOQ produit": p["moq"],
                "Auto-bid": b.get("auto_bid", False)
            })
    return pd.DataFrame(rows)


def get_max_existing_price(prod_id):
    if not st.session_state.buyers:
        return next(p["starting_price"] for p in products if p["id"] == prod_id)
    return max(
        b["products"][prod_id]["max_price"]
        for b in st.session_state.buyers
    )


# -----------------------------------
# Sidebar – Add buyer
# -----------------------------------
st.sidebar.title("➕ Ajouter un acheteur")

with st.sidebar.form("add_buyer", clear_on_submit=True):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}

    for p in products:
        st.markdown(f"**{p['name']} ({p['id']})**")

        max_existing_price = get_max_existing_price(p["id"])

        qty = st.number_input(
            f"Quantité souhaitée – {p['id']}",
            min_value=0,
            max_value=p["stock"],
            step=p["volume_multiple"],
            value=p["volume_multiple"]
        )

        price = st.number_input(
            f"Prix courant – {p['id']}",
            min_value=max_existing_price + 0.01,
            value=max_existing_price + 0.5
        )

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=price + 1.0
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    submitted = st.form_submit_button("Ajouter acheteur")

# -----------------------------------
# Submit handling
# -----------------------------------
if submitted and buyer_name:
    st.session_state.buyers.append({
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    })

    # Auto-bid immédiat
    st.session_state.buyers = run_auto_bid_aggressive(
        st.session_state.buyers,
        products
    )

    snapshot(f"Ajout acheteur + auto-bid {buyer_name}")
    st.success("Acheteur ajouté et auto-bid exécuté")

# -----------------------------------
# Main UI
# -----------------------------------
st.title("🧪 Interface de test – Allocation multi-acheteurs")

st.subheader("📦 Produits")
st.dataframe(pd.DataFrame(products), use_container_width=True)

st.subheader("👥 Acheteurs")
if st.session_state.buyers:
    st.dataframe(buyers_to_df(), use_container_width=True)
else:
    st.info("Aucun acheteur pour le moment")

# -----------------------------------
# Actions
# -----------------------------------
st.subheader("⚙️ Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Lancer allocation"):
        snapshot("Allocation manuelle")

with col2:
    if st.button("🤖 Auto-bid agressif"):
        st.session_state.buyers = run_auto_bid_aggressive(
            st.session_state.buyers,
            products
        )
        snapshot("Auto-bid manuel")

with col3:
    if st.button("🧹 Reset"):
        st.session_state.buyers = []
        st.session_state.history = []

# -----------------------------------
# Current allocation
# -----------------------------------
if st.session_state.history:
    last = st.session_state.history[-1]

    st.subheader("📊 Allocation actuelle")

    rows = []
    for b in last["buyers"]:
        for pid, qty in last["allocations"][b["name"]].items():
            price = b["products"][pid]["current_price"]
            rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Quantité allouée": qty,
                "Prix": price,
                "CA ligne": qty * price
            })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.metric("💰 Chiffre d'affaires total", f"{last['total_ca']:.2f} €")

# -----------------------------------
# History
# -----------------------------------
st.subheader("🕒 Historique")

if st.session_state.history:
    hist_df = pd.DataFrame([
        {
            "Itération": i,
            "Label": h["label"],
            "CA": h["total_ca"]
        }
        for i, h in enumerate(st.session_state.history)
    ])
    st.dataframe(hist_df, use_container_width=True)
