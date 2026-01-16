import streamlit as st
import pandas as pd
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ

# Initialisation des acheteurs dans la session
if "buyers" not in st.session_state:
    st.session_state.buyers = []
if "history" not in st.session_state:
    st.session_state.history = []

st.title("💰 Simulateur d'Enchères")

st.markdown(f"⚠️ **MOQ Global vendeur** = {SELLER_GLOBAL_MOQ} unités (tous produits confondus)")

# Ajouter un nouvel acheteur
st.subheader("Ajouter un nouvel acheteur")

with st.form("new_buyer_form"):
    buyer_name = st.text_input("Nom de l'acheteur", f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Auto-bid activé ?", value=True)
    
    buyer_products = {}
    for product in products:
        st.markdown(f"**{product['name']}** (Stock: {product['stock']}, Multiple: {product['volume_multiple']})")
        col1, col2, col3 = st.columns(3)
        with col1:
            current_price = st.number_input(f"Prix offert {product['id']}", 
                                            min_value=float(product['starting_price']),
                                            value=float(product['starting_price'] + 0.5),
                                            step=0.1)
        with col2:
            max_price = st.number_input(f"Prix max {product['id']}", 
                                        value=float(current_price + 5.0), step=0.1)
        with col3:
            qty_desired = st.number_input(f"Quantité désirée {product['id']}", min_value=1, 
                                          value=min(100, product['stock']//3), step=1)
        
        moq_default = min(30, qty_desired//2)
        moq = st.number_input(f"MOQ {product['id']}", min_value=1, value=moq_default, step=1)
        
        buyer_products[product['id']] = {
            "current_price": current_price,
            "max_price": max_price,
            "qty_desired": qty_desired,
            "moq": moq
        }
    
    submitted = st.form_submit_button("Ajouter l'acheteur")
    
    if submitted:
        new_buyer = {
            "name": buyer_name,
            "auto_bid": auto_bid,
            "products": buyer_products
        }
        st.session_state.buyers.append(new_buyer)
        st.success(f"Acheteur {buyer_name} ajouté !")
        
        # Auto-bid agressif
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        
        # Sauvegarder l'historique
        allocations, _ = solve_model(st.session_state.buyers, products)
        record = {b["name"]: allocations[b["name"]] for b in st.session_state.buyers}
        st.session_state.history.append(record)

# Affichage compact de l'état actuel
if st.session_state.buyers:
    st.subheader("État actuel des enchères")
    
    for product in products:
        prod_id = product["id"]
        st.markdown(f"**{product['name']}** (Stock: {product['stock']})")
        
        rows = []
        for buyer in st.session_state.buyers:
            alloc = solve_model(st.session_state.buyers, products)[0][buyer["name"]][prod_id]
            rows.append({
                "Acheteur": buyer["name"],
                "Prix offert": buyer["products"][prod_id]["current_price"],
                "Prix max": buyer["products"][prod_id]["max_price"],
                "Qté désirée": buyer["products"][prod_id]["qty_desired"],
                "MOQ": buyer["products"][prod_id]["moq"],
                "Alloué": alloc
            })
        
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    
    # Historique des allocations
    st.subheader("📊 Historique des allocations")
    for i, record in enumerate(st.session_state.history, 1):
        st.markdown(f"**Itération {i}**")
        hist_rows = []
        for buyer_name, allocs in record.items():
            row = {"Acheteur": buyer_name}
            row.update(allocs)
            hist_rows.append(row)
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)

