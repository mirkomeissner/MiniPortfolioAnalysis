import streamlit as st
from src.database import get_ref_data, get_all_assets_with_labels, supabase

def asset_table_view():
    st.title("Asset Static Data")
    
    if st.button("➕ New ISIN"):
        # Prepare temporary storage for the bulk form (lowercase keys)
        st.session_state["rows"] = [{
            "isin": "", "name": "", "ticker": "", "currency": "USD", 
            "price_source": "", "asset_class": "", "region": "", "sector": ""
        }]
        st.session_state["view"] = "form"
        st.rerun()

    # Display the data table
    data = get_all_assets_with_labels()
    if data:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No records found in asset_static_data.")

def asset_bulk_form():
    """Renders the bulk input form for new assets."""
    st.title("Create New Assets")
    
    # 1. Daten für Dropdowns laden (neue Tabellennamen kleingeschrieben)
    ac_dict = get_ref_data("ref_asset_class")
    reg_dict = get_ref_data("ref_region")
    sec_dict = get_ref_data("ref_sector")
    ps_dict = get_ref_data("ref_price_source")

    if all([ac_dict, reg_dict, sec_dict, ps_dict]):
        # 2. Tabellen-Header Layout
        header_cols = st.columns([1.5, 2, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5, 0.5])
        headers = ["ISIN", "Name", "Ticker", "Curr", "PriceSource", "AssetClass", "Region", "Sector", ""]
        for col, label in zip(header_cols, headers):
            col.write(f"**{label}**")

        rows_to_delete = []
        
        # 3. Dynamische Zeilen-Generierung
        for idx, row in enumerate(st.session_state["rows"]):
            cols = st.columns([1.5, 2, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5, 0.5])
            
            st.session_state["rows"][idx]["isin"] = cols[0].text_input("ISIN", value=row["isin"], key=f"isin_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["name"] = cols[1].text_input("Name", value=row["name"], key=f"name_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["ticker"] = cols[2].text_input("Ticker", value=row["ticker"], key=f"tick_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["currency"] = cols[3].text_input("Curr", value=row["currency"], key=f"curr_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["price_source"] = cols[4].selectbox("PS", options=list(ps_dict.keys()), key=f"ps_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["asset_class"] = cols[5].selectbox("AC", options=list(ac_dict.keys()), key=f"ac_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["region"] = cols[6].selectbox("Reg", options=list(reg_dict.keys()), key=f"reg_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["sector"] = cols[7].selectbox("Sec", options=list(sec_dict.keys()), key=f"sec_{idx}", label_visibility="collapsed")
            
            if cols[8].button("🗑️", key=f"del_{idx}"):
                rows_to_delete.append(idx)

        # Zeilen löschen Logik
        if rows_to_delete:
            for i in reversed(rows_to_delete):
                st.session_state["rows"].pop(i)
            st.rerun()

        st.markdown("---")
        
        # 4. Buttons im Footer
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
        
        if btn_col1.button("➕ Add Row"):
            st.session_state["rows"].append({
                "isin": "", "name": "", "ticker": "", "currency": "USD", 
                "price_source": "", "asset_class": "", "region": "", "sector": ""
            })
            st.rerun()

        if btn_col2.button("🚀 Submit All", type="primary"):
            payload = []
            valid = True
            for r in st.session_state["rows"]:
                if not r["isin"] or not r["name"]:
                    st.error("ISIN and Name are mandatory for all rows!")
                    valid = False
                    break
                
                payload.append({
                    "isin": r["isin"],
                    "name": r["name"],
                    "ticker": r["ticker"],
                    "currency": r["currency"],
                    "price_source": ps_dict[r["price_source"]],
                    "asset_class_code": ac_dict[r["asset_class"]],
                    "region_code": reg_dict[r["region"]],
                    "sector_code": sec_dict[r["sector"]],
                    "created_by": st.session_state["user_name"]
                })
            
            if valid and payload:
                try:
                    supabase.table("asset_static_data").insert(payload).execute()
                    st.success(f"✅ Successfully inserted {len(payload)} records!")
                    st.session_state["view"] = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Database Error: {e}")
        
        if btn_col3.button("Cancel"):
            st.session_state["view"] = "list"
            st.rerun()


