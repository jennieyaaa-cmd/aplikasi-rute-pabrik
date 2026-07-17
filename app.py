import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import gurobipy as gp
from gurobipy import GRB

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.set_page_config(page_title="Login Sisfo Rute", page_icon="🔐", layout="centered")
    st.title("🔐 Sistem Informasi Optimasi Rute Pabrik")
    st.write("Silakan masukkan akun operasional pabrik:")
    
    username = st.text_input("Username", value="pabriksukses")
    password = st.text_input("Password", type="password")
    
    if st.button("Login Masuk", type="primary"):
        if username == "pabriksukses" and password == "090626":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Username atau Password salah! Hubungi Admin Sistem.")
    st.stop()

st.set_page_config(page_title="Dashboard Rute Distribusi", page_icon="🚚", layout="wide")
st.title("🚚 Dashboard Optimasi Rute Distribusi (MILP-Gurobi)")
st.subheader("Sistem Pendukung Keputusan Penjadwalan Armada Harian")

with st.sidebar:
    st.markdown("### 👤 Karyawan Aktif")
    st.info("pabrikr12@gmail.com")
    st.success("🔑 Lisensi Gurobi WLS Aktif")
    if st.button("Log Out / Keluar"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown("### ⚙️ Parameter Input Operasional")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### ⏱️ Waktu Proses (Menit)")
    t_pabrik = st.number_input("Waktu Muat di Pabrik (t_pabrik)", min_value=0, value=10)
    t_retailer = st.number_input("Waktu Bongkar di Toko (t_retailer)", min_value=0, value=10)
    T_max = st.number_input("Batas Kerja Maksimal (T_max)", min_value=60, value=450)

with col2:
    st.markdown("#### 📦 Kapasitas Armada (Keranjang)")
    cap_mobil1 = st.number_input("Kapasitas Kendaraan 1", min_value=1, value=20)
    cap_mobil2 = st.number_input("Kapasitas Kendaraan 2", min_value=1, value=25)

with col3:
    st.markdown("#### 🛠️ Pengaturan Gurobi")
    time_limit = st.number_input("Batas Waktu Komputasi (detik)", min_value=5, value=30)
    M_big = st.number_input("Nilai Konstanta M (Big M)", min_value=1000, value=10000)

st.divider()

st.markdown("### 🎯 Jumlah Demand Toko (Retailer 1 - 20)")
st.caption("💡 Masukkan jumlah dalam satuan **Pieces (Pcs)**. Sistem otomatis membaginya dengan 50 dan membulatkan ke atas menjadi satuan **Keranjang** untuk MILP.")

default_demand_pcs = {
    f"R{i}": [150 if i in [1, 2, 11, 12, 16, 17] else 200 if i == 5 else 100] 
    for i in range(1, 21)
}
df_demand_pcs = pd.DataFrame(default_demand_pcs)
edited_demand_pcs = st.data_editor(df_demand_pcs, hide_index=True)

demand_converted = np.ceil(edited_demand_pcs.values[0] / 50).astype(int)
total_demand = sum(demand_converted)

st.markdown("**📋 Hasil Konversi Kebutuhan Armada (Satuan Keranjang):**")
df_hasil_keranjang = pd.DataFrame([demand_converted], columns=[f"R{i}" for i in range(1, 21)])
st.dataframe(df_hasil_keranjang, hide_index=True)

st.write(f"Total Muatan Hari Ini: **{total_demand} keranjang** | Total Kapasitas Mobil: **{cap_mobil1 + cap_mobil2} keranjang**")

st.divider()

st.markdown("### 🗺️ Matriks Waktu Perjalanan Antar Lokasi (Menit)")
st.write("Baris/Kolom 0 = Pabrik, Baris/Kolom 1-20 = Retailer 1-20. Ubah sel jika waktu jalan berubah:")

default_matrix = []
for i in range(21):
    row = []
    for j in range(21):
        if i == j:
            row.append(999999.0 if i > 0 else 0.0)
        else:
            row.append(15.0)
    default_matrix.append(row)

df_matrix = pd.DataFrame(default_matrix, 
                         columns=[f"L{i}" for i in range(21)], 
                         index=[f"L{i}" for i in range(21)])
edited_matrix = st.data_editor(df_matrix)

st.divider()

if st.button("🚀 PROSES OPTIMALISASI RUTE PABRIK", type="primary"):
    V = list(range(1, 21))
    K = [1, 2]
    Q = {1: cap_mobil1, 2: cap_mobil2}
    
    current_demand = {i: int(demand_converted[i-1]) for i in V}
    
    t_input = {}
    matrix_values = edited_matrix.values.tolist()
    for i in range(21):
        for j in range(21):
            t_input[i, j] = float(matrix_values[i][j])
            
    with st.spinner("Sedang menjalankan kalkulasi Gurobi..."):
        try:
            params = {
                "WLSACCESSID": "6b1fb55d-b2cf-4cb8-8d86-6f1fc77d9174", 
                "WLSSECRET": "680a8710-bf53-42b6-910f-8b8508b4f1a0",   
                "LICENSEID": 2818118,
            }
            
            env = gp.Env(params=params)
            model = gp.Model("MTVRP_Direct_Dashboard", env=env)
            
            model.setParam('TimeLimit', time_limit)
            model.setParam('OutputFlag', 0)
            
            x = model.addVars([(i, j, k) for i in V for j in V if i != j for k in K], vtype=GRB.BINARY, name="x")
            x_refill = model.addVars([(i, j, k) for i in V for j in V if i != j for k in K], vtype=GRB.BINARY, name="x_refill")
            start = model.addVars(V, K, vtype=GRB.BINARY, name="start")
            end = model.addVars(V, K, vtype=GRB.BINARY, name="end")
            W = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, name="W")
            Y = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, name="Y")
            
            for i in V:
                for k in K:
                    Y[i, k].ub = Q[k] - current_demand[i]
                    
            model.setObjective(
                gp.quicksum((t_input[i, j] + t_retailer) * x[i, j, k] for i in V for j in V if i != j for k in K) +
                gp.quicksum((t_input[i, 0] + t_pabrik + t_input[0, j] + t_retailer) * x_refill[i, j, k] for i in V for j in V if i != j for k in K) +
                gp.quicksum((t_pabrik + t_input[0, i]) * start[i, k] for i in V for k in K) +
                gp.quicksum(t_input[i, 0] * end[i, k] for i in V for k in K),
                GRB.MINIMIZE
            )
            
            model.addConstrs(gp.quicksum(x[i, j, k] + x_refill[i, j, k] for i in V if i != j for k in K) + gp.quicksum(start[j, k] for k in K) == 1 for j in V)
            model.addConstrs(gp.quicksum(x[i, j, k] + x_refill[i, j, k] for i in V if i != j) + start[j, k] == gp.quicksum(x[j, l, k] + x_refill[j, l, k] for l in V if j != l) + end[j, k] for j in V for k in K)
            model.addConstrs(gp.quicksum(start[i, k] for i in V) <= 1 for k in K)
            model.addConstrs(gp.quicksum(end[i, k] for i in V) <= 1 for k in K)
            model.addConstrs(Y[i, k] <= Q[k] - current_demand[i] + M_big * (1 - start[i, k]) for i in V for k in K)
            model.addConstrs(Y[j, k] <= Y[i, k] - current_demand[j] + M_big * (1 - x[i, j, k]) for i in V for j in V if i != j for k in K)
            model.addConstrs(W[i, k] >= t_pabrik + t_input[0, i] - M_big * (1 - start[i, k]) for i in V for k in K)
            model.addConstrs(W[j, k] >= W[i, k] + t_retailer + t_input[i, j] * x[i, j, k] + (t_input[i, 0] + t_pabrik + t_input[0, j]) * x_refill[i, j, k] - M_big * (2 - x[i, j, k] - x_refill[i, j, k]) for i in V for j in V if i != j for k in K)
            model.addConstrs(W[i, k] + t_retailer + t_input[i, 0] <= T_max + M_big * (1 - end[i, k]) for i in V for k in K)
            
            model.optimize()
            
            if model.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
                st.success("🎉 OPTIMASI SELESAI & BERHASIL DITEMUKAN!")
                st.metric(label="Total Waktu Operasional Armada", value=f"{round(model.ObjVal, 2)} Menit")
                
                routes_data = {}
                
                for k in K:
                    start_node = next((i for i in V if start[i, k].x > 0.5), None)
                    if start_node is not None:
                        nodes_sequence = [0, start_node]
                        route_text = f"Pabrik ➡️ R-{start_node}"
                        curr = start_node
                        while True:
                            nxt_direct = next((j for j in V if curr != j and (curr, j, k) in x and x[curr, j, k].x > 0.5), None)
                            nxt_refill = next((j for j in V if curr != j and (curr, j, k) in x_refill and x_refill[curr, j, k].x > 0.5), None)
                            
                            if nxt_direct is not None:
                                route_text += f" ➡️ R-{nxt_direct}"
                                nodes_sequence.append(nxt_direct)
                                curr = nxt_direct
                            elif nxt_refill is not None:
                                route_text += f" 🔄 [REFILL] ➡️ Pabrik ➡️ R-{nxt_refill}"
                                nodes_sequence.extend([0, nxt_refill])
                                curr = nxt_refill
                            else:
                                nodes_sequence.append(0)
                                break
                        route_text += " ➡️ Pabrik (Selesai) 🏁"
                        st.info(f"**Rute Kendaraan {k} (Kapasitas {Q[k]} Keranjang):**  \n{route_text}")
                        routes_data[k] = nodes_sequence
                    else:
                        st.warning(f"**Kendaraan {k}:** Tidak digunakan.")
                        routes_data[k] = []
                
                st.markdown("### 📊 Peta Jalur Distribusi Real-Time Per Kendaraan")
                
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9), facecolor='white')
                axes = {1: ax1, 2: ax2}
                
                for k in K:
                    ax = axes[k]
                    seq = routes_data[k]
                    
                    ax.scatter(0, 0, color='black', marker='s', s=500, zorder=5)
                    ax.text(0, 0.5, '🏢 PABRIK (L0)', fontsize=11, fontweight='bold', ha='center', va='bottom', color='black')
                    
                    if len(seq) > 2:
                        visited_in_order = []
                        visit_counter = {} 
                        
                        idx_visit = 1
                        for node in seq:
                            if node != 0:
                                visited_in_order.append(node)
                                visit_counter[node] = idx_visit
                                idx_visit += 1
                        
                        num_visited = len(visited_in_order)
                        
                        angles = np.linspace(0, 2 * np.pi, num_visited, endpoint=False)
                        
                        node_coords = {0: (0.0, 0.0)}
                        for idx, node in enumerate(visited_in_order):
                            x_n = np.cos(angles[idx]) * 5.5
                            y_n = np.sin(angles[idx]) * 5.5
                            node_coords[node] = (x_n, y_n)
                        
                        for s in range(len(seq) - 1):
                            u, v_node = seq[s], seq[s+1]
                            
                            pos_a = node_coords[u]
                            pos_b = node_coords[v_node]
                            
                            is_refill_return = (v_node == 0 and s > 1)
                            style_line = "dashed" if (u == 0 or is_refill_return) else "solid"
                            color_line = "#777777" if is_refill_return else "black"
                            
                            arrow = patches.FancyArrowPatch(
                                pos_a, pos_b,
                                arrowstyle="-|>", 
                                connectionstyle="arc3,rad=0.08", 
                                mutation_scale=16, 
                                linewidth=2.5, 
                                linestyle=style_line, 
                                color=color_line, 
                                shrinkA=22 if u != 0 else 8,
                                shrinkB=25 if v_node != 0 else 8,
                                zorder=3
                            )
                            ax.add_patch(arrow)
                        
                        for node in visited_in_order:
                            xa, ya = node_coords[node]
                            
                            ax.scatter(xa, ya, color='white', edgecolor='black', linewidth=2.5, s=1200, zorder=4)
                            
                            label_toko = f"R{node}\n(Ke-{visit_counter[node]})"
                            ax.text(xa, ya, label_toko, fontsize=9, fontweight='bold', color='black', ha='center', va='center', zorder=5)
                            
                        ax.set_title(f"🚚 JALUR DISTRIBUSI KENDARAAN {k}\n(Kapasitas: {Q[k]} Keranjang)", fontsize=13, fontweight='bold', pad=20)
                    else:
                        ax.text(0, 0, "KENDARAAN TIDAK BEROPERASI (NON-AKTIF)", fontsize=12, color='gray', ha='center', fontweight='bold')
                        ax.set_title(f"🚚 KENDARAAN {k} (Non-Aktif)", fontsize=13, fontweight='bold', pad=20)
                        
                    ax.axis('off')
                    ax.set_xlim(-7.5, 7.5)
                    ax.set_ylim(-7.5, 7.5)
                
                plt.tight_layout()
                st.pyplot(fig)
                
                buf = io.BytesIO()
                plt.savefig(buf, format="png", bbox_inches='tight', dpi=300)
                buf.seek(0)
                
                st.download_button(
                    label="📥 Download Gambar Hasil Pemetaan Rute (PNG)",
                    data=buf,
                    file_name="peta_rute_distribusi_terurut.png",
                    mime="image/png"
                )
            else:
                st.error("❌ Solusi Tidak Ditemukan (Infeasible).")
        except Exception as e:
            st.error(f"Gagal menjalankan kalkulasi: {str(e)}")
