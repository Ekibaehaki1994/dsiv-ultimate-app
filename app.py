import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="Silent.Bagger Intelligence Pro v12", layout="wide", page_icon="💎")

# --- UI STYLING (CLEAN & MODERN) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e6e6e6; }
    .card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #ffffff; }
    .text-green { color: #3fb950; font-weight: 600; }
    .text-red { color: #f85149; font-weight: 600; }
    .text-blue { color: #58a6ff; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILS ---
def format_idr(val):
    if pd.isna(val) or val == 0: return "-"
    if abs(val) >= 1e12: return f"{val/1e12:.2f} T"
    if abs(val) >= 1e9: return f"{val/1e9:.2f} M"
    return f"{val:,.0f}"

# --- DATA PREPARATION ---
default_tickers = ['ANTM', 'BBCA', 'BBRI', 'BMRI', 'ASII', 'TLKM', 'ADRO', 'PTBA']
if os.path.exists('daftar_saham_lengkap.csv'):
    df_list = pd.read_csv('daftar_saham_lengkap.csv')
    ticker_options = sorted(df_list['Kode Saham'].unique())
else:
    ticker_options = default_tickers

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Silent Bagger Pro")
    
    # Tambahkan instruksi kecil untuk user
    st.markdown("### 🎯 Input Emiten")
    
    # Fitur 1: Ketik Manual (Solusi Utama untuk HP)
    # User bisa langsung mengetik ticker apa saja (misal: UNTR, BBRI, dsb)
    custom_code = st.text_input("Ketik Kode Saham (Ticker):", placeholder="Contoh: UNTR").upper()
    
    # Fitur 2: Dropdown Pilihan (Tetap ada sebagai referensi cepat)
    selected_from_list = st.selectbox("Atau Pilih dari Daftar:", ticker_options, index=0)
    
    # Logika Penentuan: Dahulukan input manual, jika kosong gunakan selectbox
    if custom_code:
        selected_code = custom_code
    else:
        selected_code = selected_from_list
        
    st.write("---")
    st.caption(f"📍 Menganalisis: **{selected_code}**")
    st.caption("v12.0 | Market Intelligence")

# --- GLOBAL DATA SOURCE (SINKRONISASI EMITEN) ---
ticker_symbol = f"{selected_code}.JK"
# --- LOGIKA MENGHITUNG RATIO HISTORIS ---
try:
    # Ambil harga penutupan tahunan (kita ambil 5 tahun terakhir)
    hist_yearly = saham_obj.history(period="5y", interval="1d")
    # Resample untuk mendapatkan harga terakhir di setiap akhir tahun (Desember)
    yearly_price = hist_yearly['Close'].resample('YE').last().iloc[::-1] 
    
    # Ambil data EPS dan BVPS tahunan
    # Pastikan income_stmt dan balance_sheet sudah ditarik di header global
    hist_eps = income_stmt.loc['Diluted EPS'] if 'Diluted EPS' in income_stmt.index else pd.Series()
    
    # Hitung Book Value Per Share (Equity / Shares Outstanding)
    equity = balance_sheet.loc['Stockholders Equity'] if 'Stockholders Equity' in balance_sheet.index else pd.Series()
    hist_bvps = equity / shares_now
except:
    yearly_price = pd.Series()
# --- GLOBAL DATA SOURCE (SINKRONISASI EMITEN) ---
ticker_symbol = f"{selected_code}.JK"

try:
    # Buat objek utama
    saham_obj = yf.Ticker(ticker_symbol)
    inf = saham_obj.info 
    
    # Ambil semua data laporan keuangan
    actions       = saham_obj.actions 
    income_stmt   = saham_obj.income_stmt
    q_income      = saham_obj.quarterly_income_stmt
    balance_sheet = saham_obj.balance_sheet
    
    # Data harga & jumlah saham
    curr_p = inf.get('currentPrice') or inf.get('previousClose') or 0
    shares_now = inf.get('sharesOutstanding') or 1
    
    # Hitung Default Growth untuk DCF
    if not income_stmt.empty and 'Total Revenue' in income_stmt.index:
        rev_history = income_stmt.loc['Total Revenue'].iloc[::-1]
        growth_avg = rev_history.pct_change().mean()
        default_gr = float(min(max(growth_avg * 100, 0.0), 20.0))
    else:
        default_gr = 7.0

except Exception as e:
    st.error(f"⚠️ Gagal sinkronisasi data global: {e}")
    st.stop()

# --- HEADER SECTION ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"## <span class='text-blue'>{selected_code}</span> | {inf.get('longName','')}", unsafe_allow_html=True)
    st.caption(f"Sector: {inf.get('sector','-')} | Industry: {inf.get('industry','-')}")
with col_h2:
    prev_c = inf.get('previousClose', curr_p)
    change_pct = ((curr_p - prev_c) / prev_c) * 100 if prev_c != 0 else 0
    st.metric("Harga Saat Ini", f"Rp {curr_p:,.0f}", f"{change_pct:.2f}%")

# --- TABS ---
tab_tech, tab_fund, tab_pick, tab_comp, tab_accumulation = st.tabs(["🚀 STRATEGIC TECHNICAL", "⚖️ COMPLETE FUNDAMENTAL", "🎯 SMART STOCKPICK", "📊 Comparison", "🚀 Strategic Accumulation"])
# ==========================================
# TAB 1: TECHNICAL
# ==========================================
with tab_tech:
    tf_val = st.radio("Timeframe:", ["Daily (1Y)", "Weekly (1Y)", "Intraday (15m)"], index=0, horizontal=True)
    
    tf_config = {
        "Daily (1Y)": ["1y", "1d"],
        "Weekly (1Y)": ["2y", "1wk"], 
        "Intraday (15m)": ["5d", "15m"]
    }
    
    df = saham_obj.history(period=tf_config[tf_val][0], interval=tf_config[tf_val][1])
    
    if not df.empty:
        # Technical Calculation
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA50'] = ta.sma(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Simple pivots
        sup = df['Low'].rolling(window=14).min().iloc[-1]
        res = df['High'].rolling(window=14).max().iloc[-1]
        rsi_now = df['RSI'].iloc[-1]
        
        # Strategy Box
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Entry Support (Buy)", f"Rp {sup:,.0f}")
        with col2:
            st.metric("Target Resist (TP)", f"Rp {res:,.0f}")
        with col3:
            st.metric("Stop Loss (Risk)", f"Rp {sup*0.97:,.0f}")
        with col4:
            st.metric("RSI Momentum", f"{rsi_now:.2f}")
        
        # AI Insight Narrative
        status_rsi = "Oversold (Murah)" if rsi_now < 35 else "Overbought (Mahal)" if rsi_now > 70 else "Netral"
        action = "Akumulasi Bertahap" if rsi_now < 45 else "Hold / Tunggu Koreksi" if rsi_now > 65 else "Pantau Breakout"
        
        st.markdown(f"""
        <div style='margin-top: 15px; padding-top: 10px; border-top: 1px solid #30363d;'>
            <span class='text-blue'>🧠 <b>AI Strategy:</b></span> Posisi saat ini <b>{status_rsi}</b>. 
            Disarankan: <b class='text-green'>{action}</b> di area support Rp {sup:,.0f}.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Plotly Chart
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20", line=dict(color='#ff9f1c', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], name="MA50", line=dict(color='#2ec4b6', width=1)), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='#a0a0a0')), row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#3fb950", row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#f85149", row=2, col=1)
        
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 2: COMPLETE FUNDAMENTAL (FINAL CLEAN VERSION)
# ==========================================
with tab_fund:
    # --- Opsi Konversi Mata Uang ---
    col_curr1, col_curr2 = st.columns([1, 2])
    with col_curr1:
        currency_choice = st.selectbox(
            "Mata Uang Laporan Asli:",
            options=["IDR", "USD"],
            index=0,
            help="Pilih USD untuk saham seperti ADRO, HRUM, ITMG, ADMR"
        )
    
    # Tentukan kurs (Rate)
    fx_rate = 16600 if currency_choice == "USD" else 1
    
    if fx_rate > 1:
        st.warning(f"⚠️ Angka di bawah telah dikonversi dari USD ke IDR (Kurs: 16.600)")
    if income_stmt.empty or balance_sheet.empty:
        st.warning("⚠️ Laporan keuangan tidak lengkap untuk emiten ini.")
    else:
        # 1. IDENTIFIKASI KEY (Akomodasi perbedaan penamaan yfinance)
        rev_key = next((k for k in ['Total Revenue', 'Revenue'] if k in income_stmt.index), 'Total Revenue')
        net_key = next((k for k in ['Net Income', 'Net Income Common Stockholders'] if k in income_stmt.index), 'Net Income')
        equity_key = next((k for k in ['Stockholders Equity', 'Total Equity'] if k in balance_sheet.index), 'Stockholders Equity')
        eps_key = next((k for k in ['Diluted EPS', 'Basic EPS'] if k in income_stmt.index), None)
        debt_key = next((k for k in ['Total Liabilities Net Minority Interest', 'Total Liabilities'] if k in balance_sheet.index), None)

        # 2. POTONG DATA HANYA 4 TAHUN (Menghapus kolom kosong tahun ke-5/2020)
        inc_stmt_clean = income_stmt.iloc[:, :4]
        bal_sheet_clean = balance_sheet.iloc[:, :4]

        # 3. MEMBANGUN DATAFRAME UTAMA (df_full)
        df_full = pd.DataFrame({
            "Total Equity": bal_sheet_clean.loc[equity_key] if equity_key in bal_sheet_clean.index else 0,
            "Net Income": inc_stmt_clean.loc[net_key] if net_key in inc_stmt_clean.index else 0,
            "Revenue": inc_stmt_clean.loc[rev_key] if rev_key in inc_stmt_clean.index else 0,
        }).T.astype(float)
        
        # --- PERBAIKAN LOGIKA DENGAN DROPDOWN ---
        shares_list, eps_list = [], []

        for col in df_full.columns:
            try:
                # 1. Konversi angka dasar ke Rupiah berdasarkan pilihan dropdown
                net_inc_idr = df_full.loc["Net Income", col] * fx_rate
                equity_idr = df_full.loc["Total Equity", col] * fx_rate
                rev_idr = df_full.loc["Revenue", col] * fx_rate
                
                # Update tabel agar tampil dalam IDR
                df_full.loc["Net Income", col] = net_inc_idr
                df_full.loc["Total Equity", col] = equity_idr
                df_full.loc["Revenue", col] = rev_idr
                
                # 2. Ambil EPS dan konversi
                raw_eps = inc_stmt_clean.loc[eps_key, col] if eps_key in inc_stmt_clean.index else 0
                real_eps = raw_eps * fx_rate
                
                # 3. Hitung Shares Fix
                if real_eps != 0 and not pd.isna(real_eps):
                    f_eps = real_eps
                    f_shares = net_inc_idr / f_eps
                else:
                    # Fallback jika data EPS tahunan kosong (seperti kasus AADI)
                    f_shares = saham_obj.info.get('sharesOutstanding', 1)
                    f_eps = net_inc_idr / f_shares
            except:
                f_shares = saham_obj.info.get('sharesOutstanding', 1)
                f_eps = 0
            
            shares_list.append(abs(f_shares))
            eps_list.append(f_eps)

        # Update df_full dengan hasil kalibrasi
        df_full.loc["Shares Outstanding (Fix)"] = shares_list
        df_full.loc["EPS"] = eps_list

        # 3. MASUKKAN DATA FIX KE TABEL
        df_full.loc["Shares Outstanding (Fix)"] = shares_list
        df_full.loc["EPS"] = eps_list
        df_full.loc["ROE (%)"] = (df_full.loc["Net Income"] / df_full.loc["Total Equity"].replace(0, np.nan)) * 100
        
        # 5. SINKRONISASI HARGA AKHIR TAHUN
        hist_all = saham_obj.history(period="5y")
        prices = {d: (hist_all[hist_all.index.date <= pd.to_datetime(d).date()]['Close'].iloc[-1] 
                  if not hist_all[hist_all.index.date <= pd.to_datetime(d).date()].empty else curr_p) 
                  for d in df_full.columns}
        df_full.loc["Price (Year-End)"] = pd.Series(prices)

        # 6. VALUASI RATIO & AVERAGE
        bvps_series = df_full.loc["Total Equity"] / df_full.loc["Shares Outstanding (Fix)"].replace(0, np.nan)
        df_full.loc["PBV (x)"] = df_full.loc["Price (Year-End)"] / bvps_series
        df_full.loc["PER (x)"] = df_full.loc["Price (Year-End)"] / df_full.loc["EPS"]
        
        # Hitung Average dari 4 tahun data
        df_full["AVERAGE"] = df_full.mean(axis=1)

        # 7. DISPLAY TABEL UTAMA
        st.subheader("📅 Histori Fundamental & Valuasi (Scaled)")
        try:
            # 1. Ambil daftar tahun dari kolom (abaikan kolom 'AVERAGE')
            cols_tahun = [c for c in df_full.columns if c != "AVERAGE"]
            
            # 2. Hitung Pertumbuhan Tahunan Rata-rata
            num_years = len(cols_tahun) - 1
            growth_rates = []

            for index, row in df_full.iterrows():
                try:
                    val_awal = row[cols_tahun[-1]] # Data tahun tertua (paling kanan)
                    val_akhir = row[cols_tahun[0]]  # Data tahun terbaru (paling kiri)
                    
                    if val_awal > 0 and val_akhir > 0 and num_years > 0:
                        # Rumus CAGR: ((Akhir/Awal)^(1/n) - 1)
                        cagr = ((val_akhir / val_awal) ** (1/num_years) - 1) * 100
                        growth_rates.append(cagr)
                    else:
                        growth_rates.append(0)
                except:
                    growth_rates.append(0)

            # 3. Masukkan hasil hitungan ke kolom baru
            df_full["ANNUAL GROWTH (%)"] = growth_rates

            # 4. Tampilkan Tabel dengan Formatting Warna
            def style_growth(val):
                color = '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else '#848e9c'
                return f'color: {color}; font-weight: bold'

            # Menampilkan tabel yang sudah punya kolom pertumbuhan
            st.dataframe(
                df_full.style.format(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x)
                .applymap(style_growth, subset=['ANNUAL GROWTH (%)']),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Gagal memproses kolom pertumbuhan: {e}")

        # --- REVISI FINAL: DER & DIVIDEN (SINKRON & RAPI) ---
        st.write("---")
        c_fin1, c_fin2 = st.columns(2)
        
        # Ambil daftar kolom asli dari df_full agar header konsisten
        original_cols = df_full.columns

        with c_fin1:
            st.subheader("🛡️ Kesehatan Keuangan (DER)")
            if debt_key and equity_key:
                try:
                    # Ambil data DER dan pastikan urutannya sama dengan df_full
                    der_raw = (bal_sheet_clean.loc[debt_key] / bal_sheet_clean.loc[equity_key])
                    der_final = der_raw.reindex(original_cols).fillna(0)
                    
                    df_der = pd.DataFrame([der_final.values], columns=original_cols, index=["DER (x)"])
                    st.dataframe(df_der.style.format("{:.2f}"), use_container_width=True)
                except:
                    st.info("Data DER tidak tersedia.")
            else: 
                st.info("Data DER tidak tersedia.")

        with c_fin2:
            st.subheader("💰 Histori Dividen")
            # Gunakan dividends secara langsung (lebih stabil)
            div_raw = saham_obj.dividends
            
            if not div_raw.empty:
                try:
                    # 1. Kelompokkan per tahun (sum)
                    div_yearly = div_raw.groupby(div_raw.index.year).sum()
                    
                    # 2. Cocokkan dengan tahun yang ada di header df_full
                    div_values = []
                    for col in original_cols:
                        # Ekstrak tahun dari nama kolom (apapun formatnya)
                        try:
                            tahun_kolom = int(str(col)[:4])
                            # Ambil nilai dividen tahun tersebut, kali fx_rate, masukkan ke list
                            nominal = div_yearly.get(tahun_kolom, 0) * fx_rate
                            div_values.append(nominal)
                        except:
                            div_values.append(0)
                    
                    # 3. Tampilkan dengan HEADER YANG SAMA dengan DER
                    df_div_display = pd.DataFrame([div_values], columns=original_cols, index=["Dividen (IDR)"])
                    st.dataframe(df_div_display.style.format("Rp {:,.0f}"), use_container_width=True)
                except Exception as e:
                    # Jika gagal, tampilkan pesan error aslinya untuk kita perbaiki
                    st.error(f"Error: {e}")
            else: 
                st.info("Tidak ada data dividen.")

        # --- REVISI TERAMPUH: TTM vs ANNUAL (ANTI-MINUS & AUTO-FIX) ---
        st.write("---")
        st.subheader("⏱️ TTM vs Annual Comparison")
        
        if not q_income.empty:
            try:
                # 1. Identifikasi Key
                q_net_k = next((k for k in ['Net Income', 'Net Income Common Stockholders'] if k in q_income.index), None)
                q_rev_k = next((k for k in ['Total Revenue', 'Revenue'] if k in q_income.index), None)
                q_bal_sheet = saham_obj.quarterly_balance_sheet
                q_eq_k = next((k for k in ['Stockholders Equity', 'Total Equity'] if k in q_bal_sheet.index), None)
                
                # 2. Ambil Laba Bersih TTM dengan Logika Proteksi
                n_qs = q_income.loc[q_net_k].iloc[:4]
                r_net_list = []
                for i in range(len(n_qs)-1):
                    # Jika data kumulatif (Q2 > Q1), ambil selisihnya
                    if n_qs.iloc[i] > n_qs.iloc[i+1]: 
                        r_net_list.append(n_qs.iloc[i] - n_qs.iloc[i+1])
                    else:
                        r_net_list.append(n_qs.iloc[i])
                r_net_list.append(n_qs.iloc[-1])
                
                # Perbaikan: Jika total laba TTM terbaca sangat kecil atau anomali, 
                # gunakan laba tahunan terakhir sebagai batas bawah (safety net)
                ttm_net_raw = sum(r_net_list)
                ttm_net_idr = abs(ttm_net_raw) * fx_rate # Paksa positif jika ada error data YF
                
                # 3. Hitung EPS & BVPS TTM
                # Gunakan shares_now yang sudah kita ambil di awal
                eps_ttm = ttm_net_idr / shares_now if shares_now > 0 else 0
                
                latest_q_eq = q_bal_sheet.loc[q_eq_k].iloc[0] if q_eq_k else df_full.loc["Total Equity"].iloc[0]
                bvps_ttm = abs(latest_q_eq * fx_rate) / shares_now if shares_now > 0 else 0
                
                # 4. Ambil Data Annual (Dari tabel df_full)
                price_last = df_full.loc["Price (Year-End)"].iloc[0]
                eps_ann = df_full.loc["EPS"].iloc[0]
                pbv_ann = df_full.loc["PBV (x)"].iloc[0]
                per_ann = df_full.loc["PER (x)"].iloc[0]

                # 5. Susun Tabel Perbandingan
                comp_data = {
                    "Metric": ["Price", "EPS", "PER (x)", "PBV (x)"],
                    "Annual (Last)": [price_last, eps_ann, per_ann, pbv_ann],
                    "TTM (Current)": [curr_p, eps_ttm, curr_p/eps_ttm if eps_ttm > 1 else 0, curr_p/bvps_ttm if bvps_ttm > 0 else 0],
                }
                
                df_res = pd.DataFrame(comp_data)
                
                # Proteksi Growth agar tidak muncul ribuan persen jika pembagi terlalu kecil
                def calculate_growth(current, last):
                    if last <= 0: return 0
                    growth = ((current / last) - 1) * 100
                    return growth if abs(growth) < 1000 else 0 # Cap di 1000% jika anomali
                
                df_res["Changes (%)"] = [calculate_growth(row["TTM (Current)"], row["Annual (Last)"]) for _, row in df_res.iterrows()]

                st.dataframe(df_res.style.format({
                    "Annual (Last)": "{:,.2f}",
                    "TTM (Current)": "{:,.2f}",
                    "Changes (%)": "{:+.2f}%"
                }), use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"Gagal memproses TTM: {e}")

        # --- 10. RINGKASAN NILAI WAJAR (FINAL: CLEAN TABLE + NOTES) ---
        st.write("---")
        st.subheader("🎯 Ringkasan Nilai Wajar vs Harga Saat Ini")
        
        try:
            # 1. Ambil Data Dasar
            l_col = df_full.columns[0]
            eps_last = df_full.loc["EPS", l_col]
            p_avg = df_full.loc["PER (x)", "AVERAGE"]
            pb_avg = df_full.loc["PBV (x)", "AVERAGE"]
            
            equity_now = df_full.loc["Total Equity", l_col]
            shares_now = df_full.loc["Shares Outstanding (Fix)", l_col]
            bv_now = equity_now / shares_now if shares_now > 0 else 0
            
            # Variabel untuk menampung pesan peringatan
            warnings = []
            
            # 2. Logika Valuasi dengan Filter Ketat
            # Graham Number
            if eps_last > 0 and bv_now > 0:
                g_val = (22.5 * eps_last * bv_now)**0.5
            else:
                g_val = 0
                warnings.append("⚠️ **Graham Number N/A**: Laba per saham (EPS) atau Ekuitas bernilai negatif.")

            # PER Reversion
            if eps_last > 0:
                per_t = eps_last * p_avg
            else:
                per_t = 0
                warnings.append("⚠️ **PER Reversion N/A**: Perusahaan sedang mencatat kerugian (EPS Minus).")

            # PBV Reversion
            pbv_t = bv_now * pb_avg

            # 3. Susun Data (HANYA KOLOM UTAMA)
            data_final = [
                {"Metode": "Graham Number", "Nilai": g_val},
                {"Metode": "PER Mean Reversion", "Nilai": per_t},
                {"Metode": "PBV Mean Reversion", "Nilai": pbv_t}
            ]
            
            df_res = pd.DataFrame(data_final)

            # 4. Hitung Upside
            df_res["Upside (%)"] = df_res["Nilai"].apply(
                lambda x: ((x / curr_p) - 1) * 100 if x > 0 else None
            )

            # 5. Tampilan UI
            st.info(f"💡 **Harga Pasar Saat Ini: Rp {curr_p:,.0f}**")

            def style_row(row):
                if pd.isna(row["Upside (%)"]):
                    return ['color: #848e9c'] * len(row)
                color = '#2ecc71' if row["Upside (%)"] > 0 else '#e74c3c'
                return [f'color: {color}'] * len(row)

            # Tampilkan Tabel
            st.dataframe(
                df_res.style.format({
                    "Nilai": lambda x: f"Rp {x:,.0f}" if x > 0 else "N/A",
                    "Upside (%)": lambda x: f"{x:+.1f}%" if pd.notnull(x) else "-"
                }).apply(style_row, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # 6. KETERANGAN DI BAWAH TABEL (Hanya muncul jika ada anomali)
            if warnings:
                for msg in warnings:
                    st.caption(msg)
            else:
                st.caption("✅ Semua metode valuasi berhasil dihitung menggunakan data fundamental terbaru.")

        except Exception as e:
            st.error(f"Gagal memproses ringkasan: {e}")
    # ==================================================
        # 10. ADVANCED DCF WITH AUTO-HISTORICAL GROWTH (FIXED & STABLE)
        # ==================================================
        st.write("---")
        st.subheader("📉 Advanced DCF Analysis (Smart Historical Growth)")

        try:
            # 1. PENGAMBILAN DATA HISTORIS UNTUK GROWTH
            financials = saham_obj.financials
            if not financials.empty and 'Total Revenue' in financials.index:
                rev_history = financials.loc['Total Revenue'].iloc[::-1]
                growth_series = rev_history.pct_change().dropna()
                avg_growth_hist = float(growth_series.mean() * 100)
                # Batasi growth historis agar masuk akal (0% - 20%)
                default_gr = float(min(max(avg_growth_hist, 0.0), 20.0))
            else:
                default_gr = 7.0 

            # 2. STABILISASI DATA DASAR (PENTING!)
            # Gunakan EPS Annual terakhir dari tabel df_full agar angka tidak anomali
            # Kita asumsikan EPS adalah 'Proxy' dari Cash Flow per share
            eps_base = df_full.loc["EPS"].iloc[0]
            
            # Jika EPS minus (seperti KIJA), DCF tidak bisa dihitung secara akurat
            if eps_base <= 0:
                st.warning("⚠️ DCF tidak ideal untuk saham dengan laba negatif.")
                eps_base = 0

            # Harga dan Jumlah Saham
            price_now = curr_p
            shares_now = saham_obj.info.get('sharesOutstanding', 1)

            # 3. UI PARAMETER
            with st.expander("⚙️ Konfigurasi Parameter (Auto-Detected)", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    dr = st.slider("Discount Rate (WACC) %", 8.0, 20.0, 12.0, 0.5) / 100
                with c2:
                    gr = st.slider("Expected Growth (4Y) %", 0.0, 25.0, default_gr, 0.5) / 100
                    st.caption(f"💡 Historis Revenue: **{default_gr:.1f}%**")
                with c3:
                    tg = st.slider("Terminal Growth %", 1.0, 5.0, 3.0, 0.5) / 100

            # 4. PERHITUNGAN DCF (Berdasarkan EPS Base)
            # Rumus: Mencari Present Value dari pertumbuhan EPS 5 tahun ke depan
            cashflows = []
            for i in range(1, 6):
                future_eps = eps_base * ((1 + gr) ** i)
                pv_eps = future_eps / ((1 + dr) ** i)
                cashflows.append(pv_eps)

            # Terminal Value
            terminal_val = (future_eps * (1 + tg)) / (dr - tg)
            terminal_pv = terminal_val / ((1 + dr) ** 5)

            # Nilai Intrinsik per Saham
            dcf_intrinsic = sum(cashflows) + terminal_pv
            
            # Hitung Upside
            dcf_upside = ((dcf_intrinsic - price_now) / price_now) * 100 if price_now > 0 else 0

            # 5. TAMPILAN CARD UI
            dcf_color = "#2ecc71" if dcf_upside > 15 else "#f1c40f" if dcf_upside > 0 else "#e74c3c"
            
            st.markdown(f"""
                <div style="background-color:#1e2329; padding:25px; border-radius:15px; border-left: 8px solid {dcf_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <p style="color:#848e9c; margin:0; font-size:14px;">ESTIMASI NILAI WAJAR (DCF)</p>
                            <h2 style="margin:0; color:white;">Rp {dcf_intrinsic:,.0f}</h2>
                        </div>
                        <div style="text-align:right;">
                            <p style="color:#848e9c; margin:0; font-size:14px;">POTENSI UPSIDE</p>
                            <h2 style="margin:0; color:{dcf_color};">{dcf_upside:+.1f}%</h2>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ Gagal menghitung DCF: {e}")
# ==========================================
# TAB 3: SMART PICK (FULL LIST RESTORED)
# ==========================================
with tab_pick:
    st.subheader("🌙 Advanced Shariah Screener (ISSI Scope)")
    st.caption("Scanning otomatis berdasarkan Daftar Efek Syariah (DES) dengan deteksi Volume Accumulation & Risk Management.")

    # --- FULL CATEGORIES RESTORED ---
    categories = {
        "Energi (Batu Bara, Oil & Gas)": [
            'ADRO.JK', 'PTBA.JK', 'ITMG.JK', 'HRUM.JK', 'MEDC.JK', 'PGAS.JK',
            'ENRG.JK', 'DEWA.JK', 'MBMA.JK', 'TINS.JK', 'KKGI.JK', 'AKRA.JK',
            'INDY.JK', 'TOBA.JK', 'BSSR.JK', 'SMMT.JK', 'ARII.JK', 'RMKE.JK',
            'ELSA.JK', 'RAJA.JK', 'PSSI.JK', 'GEMS.JK', 'MBAP.JK', 'DOID.JK',
            'WINS.JK', 'APEX.JK', 'ABMM.JK', 'FIRE.JK', 'COAL.JK', 'BUMI.JK',
            'BYAN.JK', 'PTRO.JK', 'MYOH.JK', 'GTBO.JK', 'SMRU.JK', 'ZINC.JK',
            'PSAB.JK', 'ESSA.JK', 'RIGS.JK', 'SOCS.JK', 'TMAS.JK', 'LEAD.JK',
            'HITS.JK', 'IPCM.JK', 'MINE.JK', 'MINA.JK'
        ],
        "Barang Konsumsi & Kesehatan": [
    'ICBP.JK', 'INDF.JK', 'UNVR.JK', 'KLBF.JK', 'SIDO.JK', 'MYOR.JK',
    'AMRT.JK', 'CPIN.JK', 'MIKA.JK', 'HEAL.JK', 'SILO.JK', 'CLEO.JK',
    'GOOD.JK', 'ULTJ.JK', 'KAEF.JK', 'INAF.JK', 'PYFA.JK', 'DVLA.JK',
    'PRDA.JK', 'HOKI.JK', 'ROTI.JK', 'STTP.JK', 'SKBM.JK', 'AISA.JK',
    'TSPC.JK', 'PANI.JK', 'PEHA.JK', 'ERAA.JK',
    'HMSP.JK', 'GGRM.JK', 'WIIM.JK', 'CEKA.JK', 'JPFA.JK', 'SOHO.JK',
    'MERK.JK', 'SRAJ.JK', 'SAME.JK', 'CARE.JK', 'RALS.JK', 'ACES.JK',
    'MAPI.JK', 'MAPA.JK', 'MAPB.JK', 'FAST.JK', 'WICO.JK'
        ],
        "Infrastruktur & Telekomunikasi": [
            'TLKM.JK', 'EXCL.JK', 'JSMR.JK', 'WIFI.JK', 'MTEL.JK',
            'TOWR.JK', 'TBIG.JK', 'ISAT.JK', 'IBST.JK', 'LINK.JK',
            'OASA.JK', 'META.JK', 'KEEN.JK', 'POWR.JK', 'TGRA.JK',
            'BCPT.JK', 'JPRS.JK', 'CPRO.JK'
        ],
        "Keuangan Syariah & Investasi": [
            'BRIS.JK', 'BTPS.JK', 'PNBS.JK', 'BTPN.JK', 'SRTG.JK', 'MLPT.JK',
            'ADMF.JK', 'BFI.JK', 'CFIN.JK', 'WOMF.JK', 'MREI.JK', 'TRIM.JK',
            'BBMI.JK', 'PNMF.JK'
        ],
        "Properti & Konstruksi Syariah": [
            'BSDE.JK', 'CTRA.JK', 'SMRA.JK', 'PWON.JK', 'SMGR.JK',
            'INTP.JK', 'ADHI.JK', 'PTPP.JK', 'WIKA.JK', 'SSIA.JK',
            'DMAS.JK', 'JRPT.JK', 'MTLA.JK', 'KIJA.JK', 'DILD.JK',
            'BKSL.JK', 'ASRI.JK', 'TOTAL.JK', 'WSKT.JK', 'CTSN.JK'
        ],
        "Teknologi & Ekonomi Digital": [
            'BUKA.JK', 'BELI.JK', 'ASSA.JK', 'ELANG.JK', 'DMMX.JK', 'WIRG.JK',
            'MCAS.JK', 'KIOS.JK', 'EDGE.JK', 'TECH.JK', 'GOTO.JK', 'MTDL.JK',
            'CASH.JK', 'LUCK.JK'
        ],
        "Industri Dasar & Kimia": [
            'BRPT.JK', 'TPIA.JK', 'INKP.JK', 'TKIM.JK', 'MDKA.JK',
            'ANJT.JK', 'AVIA.JK', 'ESSA.JK', 'IMPC.JK', 'ALKA.JK',
            'FASW.JK', 'NICC.JK', 'BMTR.JK', 'JPFA.JK',
            'ANTM.JK', 'INCO.JK', 'SMGP.JK', 'BRMS.JK', 'PURA.JK'
        ],
        "Transportasi & Logistik": [
            'BIRD.JK', 'TMAS.JK', 'SMDR.JK', 'GIAA.JK', 'NELI.JK',
            'WEHA.JK', 'SAPX.JK', 'JAYA.JK', 'HAIS.JK',
            'BULL.JK', 'PANO.JK', 'CMPP.JK', 'NELY.JK', 'TPJA.JK'
        ],
        "Pertanian (CPO)": [
            'AALI.JK', 'LSIP.JK', 'BWPT.JK', 'TAPG.JK', 'DSNG.JK', 'SIMP.JK',
            'PSGO.JK', 'SSMS.JK', 'GZCO.JK', 'PALM.JK',
            'SGRO.JK', 'STAA.JK', 'TBLA.JK', 'MAGP.JK', 'JAWA.JK'
        ]
    }

    selected_category = st.selectbox("Pilih Sektor Syariah:", list(categories.keys()))
    tickers_to_scan = categories[selected_category]

    if st.button(f"🚀 Mulai Analisis Komprehensif ({len(tickers_to_scan)} Emiten)"):
        fund_picks = []
        tech_picks = []
        
        # UI Progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, t in enumerate(tickers_to_scan):
            try:
                status_text.caption(f"Scanning: {t}...")
                s = yf.Ticker(t)
                h = s.history(period="6mo") # Optimasi: scan 6 bulan cukup untuk teknikal
                inf = s.info
                
                if h.empty or len(h) < 20: continue
                
                # --- CALCS ---
                current_p = h['Close'].iloc[-1]
                rsi = ta.rsi(h['Close'], length=14).iloc[-1]
                ma20 = h['Close'].rolling(window=20).mean().iloc[-1]
                
                # 1. Fundamental Screener
                eps = inf.get('trailingEps', 0)
                bvps = inf.get('bookValue', 0)
                roe = inf.get('returnOnEquity', 0) * 100
                
                if eps and bvps and eps > 0 and bvps > 0:
                    graham = (22.5 * eps * bvps)**0.5
                    # Kriteria: Harga di bawah Graham ATAU PBV Murah, dengan ROE positif
                    if (graham > current_p or inf.get('priceToBook', 2) < 1.2) and roe > 5:
                        fund_picks.append({
                            "Ticker": t.replace(".JK", ""),
                            "Entry": current_p,
                            "Graham": graham,
                            "ROE": roe,
                            "Upside": ((graham - current_p)/current_p)*100
                        })

                # 2. Technical Screener
                # Kriteria: Oversold (RSI < 40) ATAU Golden Cross (Price cross MA20)
                if rsi < 40 or (current_p > ma20 and h['Close'].iloc[-2] < ma20):
                    sig = "Oversold" if rsi < 40 else "Breakout"
                    tech_picks.append({
                        "Ticker": t.replace(".JK", ""),
                        "Entry": current_p,
                        "Signal": sig,
                        "RSI": rsi,
                        "TP": current_p * 1.05
                    })
                    
            except:
                continue
            progress_bar.progress((i + 1) / len(tickers_to_scan))

        status_text.empty()
        progress_bar.empty()

        # DISPLAY RESULTS
        st.write("---")
        col1, col2 = st.columns(2)

        with col1:
            st.success("💎 Top Fundamental Syariah")
            if fund_picks:
                df_f = pd.DataFrame(fund_picks)
                st.dataframe(
                    df_f.sort_values(by="Upside", ascending=False).head(20).style.format({
                        "Entry": "{:,.0f}", "Graham": "{:,.0f}", "ROE": "{:.1f}%", "Upside": "{:+.1f}%"
                    }), use_container_width=True, hide_index=True
                )
            else:
                st.info("Tidak ada saham value investing ditemukan.")

        with col2:
            st.info("📊 Top Technical Momentum")
            if tech_picks:
                df_t = pd.DataFrame(tech_picks)
                st.dataframe(
                    df_t.sort_values(by="RSI", ascending=True).head(20).style.format({
                        "Entry": "{:,.0f}", "RSI": "{:.1f}", "TP": "{:,.0f}"
                    }), use_container_width=True, hide_index=True
                )
            else:
                st.info("Tidak ada sinyal teknikal (Oversold/Breakout).")
# ==========================================
# TAB 3: ADVANCED COMPARISON (METRICS TUNED)
# ==========================================
with tab_comp:
    st.subheader("📊 Multi-Stock Comparison Matrix")
    
    default_comp = f"{ticker}, BBRI.JK, BMRI.JK, BBNI.JK" if 'ticker' in locals() else "BBCA.JK, BBRI.JK, BMRI.JK"
    comparison_tickers = st.text_input("Masukkan Kode Saham:", value=default_comp).upper()

    if comparison_tickers:
        tickers_list = [t.strip() for t in comparison_tickers.split(",")]
        comp_results = []

        with st.spinner('Menghitung data emiten...'):
            for t_symbol in tickers_list:
                try:
                    t_obj = yf.Ticker(t_symbol)
                    t_info = t_obj.info
                    t_inc = t_obj.income_stmt.iloc[:, :4]
                    t_bal = t_obj.balance_sheet.iloc[:, :4]
                    t_q_inc = t_obj.quarterly_income_stmt # Data kuartalan

                    if t_inc.empty or t_bal.empty: continue

                    # 1. BASIC KEYS
                    c_price = t_info.get('currentPrice', t_info.get('previousClose', 0))
                    eps_k = next((k for k in ['Diluted EPS', 'Basic EPS'] if k in t_inc.index), None)
                    net_k = next((k for k in ['Net Income', 'Net Income Common Stockholders'] if k in t_inc.index), None)
                    eq_k = next((k for k in ['Stockholders Equity', 'Total Equity'] if k in t_bal.index), None)
                    liab_k = next((k for k in ['Total Liabilities Net Minority Interest', 'Total Liabilities'] if k in t_bal.index), None)

                    # --- REVISI LOGIKA TTM TAB 3 (COMPARE) ---
                    if not t_q_inc.empty:
                        q_net_k = next((k for k in ['Net Income', 'Net Income Common Stockholders'] if k in t_q_inc.index), None)
                        if q_net_k:
                            # Ambil 4 kuartal, bersihkan dari efek kumulatif
                            n_qs = t_q_inc.loc[q_net_k].iloc[:4]
                            r_net = []
                            for i in range(len(n_qs)-1):
                                if n_qs.iloc[i] > n_qs.iloc[i+1]: # Deteksi Kumulatif
                                    r_net.append(n_qs.iloc[i] - n_qs.iloc[i+1])
                                else:
                                    r_net.append(n_qs.iloc[i])
                            r_net.append(n_qs.iloc[-1])
                            
                            ttm_net_total = sum(r_net)
                            # Gunakan shares_outstanding dari info agar konsisten
                            s_out = t_info.get('sharesOutstanding', 1)
                            eps_ttm_val = ttm_net_total / s_out
                        else:
                            eps_ttm_val = t_info.get('trailingEps', eps_ann)
                    else:
                        eps_ttm_val = t_info.get('trailingEps', eps_ann)

                    # 3. EPS GROWTH 4Y (CAGR)
                    if eps_k and len(t_inc.columns) >= 4:
                        v_final, v_start = t_inc.loc[eps_k].iloc[0], t_inc.loc[eps_k].iloc[-1]
                        growth_avg = (((v_final / v_start) ** (1/3)) - 1) * 100 if v_start > 0 else 0
                    else: growth_avg = 0

                    # 4. SHARES & VALUATION SCALING
                    latest_net = t_inc.loc[net_k].iloc[0]
                    eps_ann = t_inc.loc[eps_k].iloc[0] if eps_k else 0
                    s_fix = abs(latest_net / eps_ann) if eps_ann != 0 else t_info.get('sharesOutstanding', 1)
                    
                    latest_eq = t_bal.loc[eq_k].iloc[0]
                    bvps = latest_eq / s_fix
                    
                    # 5. DER (ANNUAL & TTM ESTIMATE)
                    der_ann = (t_bal.loc[liab_k].iloc[0] / latest_eq) if liab_k and latest_eq > 0 else 0
                    # TTM DER menggunakan ekuitas kuartal terbaru
                    latest_q_eq = t_obj.quarterly_balance_sheet.loc[eq_k].iloc[0] if eq_k in t_obj.quarterly_balance_sheet.index else latest_eq
                    latest_q_liab = t_obj.quarterly_balance_sheet.loc[liab_k].iloc[0] if liab_k in t_obj.quarterly_balance_sheet.index else 0
                    der_ttm = latest_q_liab / latest_q_eq if latest_q_eq > 0 else der_ann

                    # 6. DIVIDEN NOMINAL TERAKHIR
                    last_div = 0
                    if not t_obj.actions.empty:
                        divs = t_obj.actions[t_obj.actions['Dividends'] > 0]
                        last_div = divs['Dividends'].iloc[-1] if not divs.empty else 0

                    comp_results.append({
                        "Ticker": t_symbol,
                        "Price": c_price,
                        "PBV (x)": c_price / bvps if bvps > 0 else 0,
                        "PER (x)": c_price / eps_ttm_val if eps_ttm_val > 0 else 0,
                        "EPS Growth 4Y": growth_avg,
                        "EPS Annual": eps_ann,
                        "EPS TTM": eps_ttm_val,
                        "Last Div": last_div,
                        "DER Annual": der_ann,
                        "DER TTM": der_ttm,
                        "ROE (%)": (latest_net / latest_eq) * 100 if latest_eq > 0 else 0
                    })
                except: continue

        if comp_results:
            df_comp = pd.DataFrame(comp_results)
            st.dataframe(
                df_comp.style.format({
                    "Price": "{:,.0f}", "PBV (x)": "{:.2f}", "PER (x)": "{:.2f}",
                    "EPS Growth 4Y": "{:+.2f}%", "EPS Annual": "{:.2f}", "EPS TTM": "{:.2f}",
                    "Last Div": "Rp {:.2f}", "DER Annual": "{:.2f}", "DER TTM": "{:.2f}", "ROE (%)": "{:.2f}%"
                }).highlight_max(subset=['ROE (%)', 'EPS Growth 4Y'], color='#1e4620')
                  .highlight_min(subset=['PER (x)', 'PBV (x)', 'DER TTM'], color='#1e4620'),
                use_container_width=True, hide_index=True
            )
            
            # Perbandingan Visual ROE vs DER (Risk vs Reward)
            st.write("---")
            fig_risk = px.scatter(df_comp, x="DER TTM", y="ROE (%)", text="Ticker", size="Price",
                                 title="Risk (DER) vs Reward (ROE) Comparison",
                                 labels={"DER TTM": "Debt to Equity Ratio (TTM)", "ROE (%)": "Return on Equity (%)"})
            fig_risk.update_traces(textposition='top center')
            fig_risk.update_layout(template="plotly_dark")
            st.plotly_chart(fig_risk, use_container_width=True)
        else:
            st.error("Gagal menarik data. Pastikan simbol menggunakan .JK")
with tab_accumulation:
    st.subheader("🚀 DSIV Formula (Dynamic Strategic Intrinsic Valuation)")
    st.write("Formula orisinil untuk memproyeksikan harga masa depan berdasarkan internal compounding perusahaan.")

    try:
        # --- 1. DATA PREPARATION ---
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        currency = info.get('currency', 'IDR')
        l_col = df_full.columns[0]

        # --- 2. INISIALISASI VARIABEL (Pencegah Error 'Not Defined') ---
        ttm_roe = 0.0
        hist_roe = 0.0
        auto_roe = 0.0
        raw_equity = 0.0
        raw_shares = 0.0
        calc_bvps = 0.0
        calc_wqf = 1.0
        exchange_rate = 1.0

        # Currency Shield
        if currency == 'USD':
            try:
                rate_ticker = yf.Ticker("USDIDR=X")
                exchange_rate = rate_ticker.fast_info['last_price']
            except:
                exchange_rate = 15800
            st.warning(f"⚠️ Konversi USD ke IDR Aktif (Kurs: {exchange_rate:,.0f})")

        # --- 3. LOGIKA PENCARIAN DATA ---
        def get_row_data(keywords, default=0):
            for row_name in df_full.index:
                if any(k.lower() in row_name.lower() for k in keywords):
                    try:
                        return float(df_full.loc[row_name, l_col])
                    except:
                        continue
            return default

        # Ambil Data Dasar
        raw_equity = get_row_data(["Total Equity", "Equity"])
        raw_shares = get_row_data(["Shares Outstanding", "Shares Fix"])
        calc_bvps = (raw_equity / raw_shares) * exchange_rate if raw_shares != 0 else 0

        # Hitung ROE & PBV
        try:
            roe_idx = [x for x in df_full.index if "ROE" in x][0]
            hist_cols = [c for c in df_full.columns if c != 'AVERAGE']
            hist_roe = float(df_full.loc[roe_idx, hist_cols].median())
            ttm_roe = float(df_full.loc[roe_idx, l_col])
            auto_roe = (hist_roe + ttm_roe) / 2
            
            pbv_idx = [x for x in df_full.index if "PBV" in x][0]
            avg_pbv = float(df_full.loc[pbv_idx, "AVERAGE"])
            curr_pbv_val = float(df_full.loc[pbv_idx, l_col])
            calc_wqf = (0.7 * avg_pbv) + (0.3 * curr_pbv_val)
        except:
            auto_roe, calc_wqf = 10.0, 1.0

        # --- 4. SESSION STATE MANAGEMENT (Anti-Reset) ---
        if 'dsiv_last_ticker' not in st.session_state or st.session_state.dsiv_last_ticker != ticker_symbol:
            st.session_state.dsiv_last_ticker = ticker_symbol
            st.session_state.final_bvps = calc_bvps
            st.session_state.final_roe = auto_roe
            st.session_state.final_wqf = calc_wqf

        # --- 5. CALIBRATION CHAMBER (Form) ---
        with st.form("dsiv_final_form"):
            st.markdown("### 🛠️ Calibration Chamber")
            c1, c2, c3 = st.columns(3)
            with c1:
                input_bvps = st.number_input("Adjusted BVPS", value=float(st.session_state.final_bvps))
            with c2:
                input_roe = st.number_input("Expected ROE (%)", value=float(st.session_state.final_roe))
            with c3:
                input_wqf = st.number_input("Adjusted WQF", value=float(st.session_state.final_wqf))
            submitted = st.form_submit_button("🔥 Apply Changes & Run DSIV")

        if submitted:
            st.session_state.final_bvps = input_bvps
            st.session_state.final_roe = input_roe
            st.session_state.final_wqf = input_wqf
            st.success("✅ Data tersimpan! Menghitung ulang...")
            st.rerun()

        # Final Variables untuk Perhitungan
        f_bvps = st.session_state.final_bvps
        f_roe = st.session_state.final_roe / 100
        f_wqf = st.session_state.final_wqf

        # --- 6. CALCULATIONS & DISPLAY ---
        tp1_floor = f_bvps * f_wqf
        tp2_target = (f_bvps * (1 + f_roe)) * f_wqf

        st.write("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Price", f"Rp {curr_p:,.0f}")
        up1 = ((tp1_floor/curr_p)-1)*100 if curr_p != 0 else 0
        up2 = ((tp2_target/curr_p)-1)*100 if curr_p != 0 else 0
        m2.metric("TP 1 (Floor)", f"Rp {tp1_floor:,.0f}", f"{up1:+.1f}%")
        m3.metric("TP 2 (Target)", f"Rp {tp2_target:,.0f}", f"{up2:+.1f}%")

        # Action Signal
        st.markdown("### 🚦 DSIV Execution Signal")
        if curr_p < tp1_floor:
            st.success("### 💎 BUY / ACCUMULATE")
        elif curr_p < tp2_target:
            st.warning("### ⚖️ HOLD / MONITOR")
        else:
            st.error("### 🚩 TAKE PROFIT / OVERVALUED")

        # --- 7. EXECUTIVE SUMMARY ---
        st.write("---")
        st.subheader("📝 DSIV Analyst Note")
        implied_growth = f_roe * 100
        col_text, col_metric = st.columns([2, 1])
        with col_text:
            st.markdown(f"""
            **Outlook Masa Depan:**
            Berdasarkan efisiensi modal, nilai intrinsik tumbuh secara internal sebesar **{implied_growth:.2f}% per tahun**.
            Target **Rp {tp2_target:,.0f}** mengasumsikan pasar tetap menghargai kualitas aset di level PBV **{f_wqf:.2f}x**.
            """)
        with col_metric:
            st.metric("Implied Growth", f"{implied_growth:.1f}%")
            st.metric("Multiplier", f"{f_wqf:.2f}x")

        # --- 8. AUDIT RAIL (Transparansi Data) ---
        with st.expander("🔍 Lihat Detail Perhitungan Otomatis (Audit Rail)"):
            st.write("### Audit Data Fundamental")
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                st.write("**Profitabilitas:**")
                st.write(f"- ROE Terbaru (TTM): `{ttm_roe:.2f}%`")
                st.write(f"- Median Historis: `{hist_roe:.2f}%`")
                st.write(f"- **Final Auto ROE: `{auto_roe:.2f}%`**")
            with c_a2:
                st.write("**Aset & Modal:**")
                st.write(f"- Total Equity: `Rp {raw_equity:,.0f}`")
                st.write(f"- Shares: `{raw_shares:,.0f}`")
                st.write(f"- **BVPS: `Rp {calc_bvps:,.2f}`**")

    except Exception as e:

        st.error(f"⚠️ Terjadi kesalahan pada DSIV: {e}")
