import streamlit as st
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ
import copy

st.set_page_config(page_title="Simulateur d'enchères", layout="wide")

# -----------------------------
# INITIALISATION SESSION STATE
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Helper functions
# -----------------------------
def update_allocations():
    # Clone buyers to avoid overwriting
    st.session_state.buyers = run_auto_bid_aggressive(copy.deepcopy(st.session_state.buyers), products)
    
    # Stocke l'état actuel dans l'historique
    record = {}
    for b in st.session_state.buyers:
        record[b["name"]] = {}
        for p in products:
            pid = p["id"]
            pdata = b["products"][pid]
            allocs, _ = solve_model([b], products)
            record[b["name"]][pid] = {
                "allocated": allocs[b["name"]][pid],
                "current_price": pdata["current_price"],
                "max_price": pdata["max_price"],
                "qty_desired": pdata["qty_desired"]
            }
    st.session_state.history.append(record)
    
    return record

# -----------------------------
# Affichage informations produits
# -----------------------------
st.sidebar.markdown("### Produits disponibles")
for p in products:
    st.sidebar.write(f"{p['name']} ({p['id']}): Stock={p['stock']} | Multiple={p['volume_multiple']} | Prix départ={p['starting_price']:.2f}€")

# -----------------------------
# Ajouter un nouvel acheteur
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### Ajouter un acheteur")
with st.sidebar.form("add_buyer"):
    buyer_name = st.text_input("Nom de l'acheteur", value=f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Auto-bid activé ?", value=True)
    
    new_buyer_data = {}
    for p in products:
        pid = p["id"]
        col1, col2, col3 = st.columns(3)
        with col1:
            qty = st.number_input(f"{p['name']} - Qté désirée", min_value=1, step=p["volume_multiple"], value=min(100, p["stock"] // 3), key=f"{buyer_name}_{pid}_qty")
        with col2:
            price = st.number_input(f"{p['name']} - Prix offert", min_value=p["starting_price"], step=0.05, value=p["starting_price"]+0.5, key=f"{buyer_name}_{pid}_price")
        with col3:
            max_price = st.number_input(f"{p['name']} - Prix max", min_value=price, step=0.05, value=price+5.0, key=f"{buyer_name}_{pid}_max")
        
        new_buyer_data[pid] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": min(30, qty // 2)
        }
    
    submitted = st.form_submit_button("Ajouter l'acheteur")
    if submitted:
        st.session_state.buyers.append({
            "name": buyer_name,
            "auto_bid": auto_bid,
            "products": new_buyer_data
        })
        update_allocations()
        st.success(f"Acheteur {buyer_name} ajouté et allocations recalculées.")

# -----------------------------
# Modifier un acheteur existant
# -----------------------------
if st.session_state.buyers:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Modifier un acheteur")
    buyer_to_edit = st.sidebar.selectbox("Sélectionner un acheteur", [b["name"] for b in st.session_state.buyers], key="edit_select")
    if buyer_to_edit:
        b = next(b for b in st.session_state.buyers if b["name"] == buyer_to_edit)
        st.sidebar.markdown(f"**Modifier {buyer_to_edit}**")
        for p in products:
            pid = p["id"]
            pdata = b["products"][pid]
            col1, col2 = st.sidebar.columns(2)
            with col1:
                new_price = st.number_input(f"{p['name']} - Prix offert", min_value=p["starting_price"], step=0.05, value=pdata["current_price"], key=f"edit_{buyer_to_edit}_{pid}_price")
            with col2:
                new_max = st.number_input(f"{p['name']} - Prix max", min_value=new_price, step=0.05, value=pdata["max_price"], key=f"edit_{buyer_to_edit}_{pid}_max")
            
            pdata["current_price"] = new_price
            pdata["max_price"] = new_max
        
        if st.sidebar.button(f"Recalculer allocations pour {buyer_to_edit}"):
            update_allocations()
            st.sidebar.success(f"Allocations recalculées pour {buyer_to_edit}")

# -----------------------------
# Affichage des allocations actuelles
# -----------------------------
st.markdown("## État actuel des allocations")
if st.session_state.buyers:
    allocs = update_allocations()
    # Construire le tableau
    table_data = []
    for b in st.session_state.buyers:
        row = {"Acheteur": b["name"]}
        for p in products:
            pid = p["id"]
            pdata = b["products"][pid]
            alloc_info = allocs[b["name"]][pid]
            row[f"{pid} (Qté désirée)"] = pdata["qty_desired"]
            row[f"{pid} (Prix offert)"] = alloc_info["current_price"]
            row[f"{pid} (Prix max)"] = alloc_info["max_price"]
            row[f"{pid} (Alloué)"] = alloc_info["allocated"]
        table_data.append(row)
    
    st.table(table_data)
else:
    st.info("Aucun acheteur pour l'instant.")

# -----------------------------
# Historique des allocations
# -----------------------------
st.markdown("## Historique des allocations")
if st.session_state.history:
    for i, record in enumerate(st.session_state.history):
        st.markdown(f"### Itération {i+1}")
        table_data = []
        for buyer_name, buyer_allocs in record.items():
            row = {"Acheteur": buyer_name}
            for pid, alloc_info in buyer_allocs.items():
                row[f"{pid} (Qté désirée)"] = alloc_info["qty_desired"]
                row[f"{pid} (Prix offert)"] = alloc_info["current_price"]
                row[f"{pid} (Prix max)"] = alloc_info["max_price"]
                row[f"{pid} (Alloué)"] = alloc_info["allocated"]
            table_data.append(row)
        st.table(table_data)
else:
    st.info("Aucune itération pour le moment.")
