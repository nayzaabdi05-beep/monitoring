import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, ConfusionMatrixDisplay
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Konfigurasi Layout Halaman Menjadi Lebar
st.set_page_config(page_title="Sistem Monitoring & Prediksi PT Epsindo", layout="wide")

# --- HEADER UTAMA SISTEM ---
st.title("Sistem Monitoring Bulanan")
st.markdown("### PT Epsindo Jaya Pratama Workshop Duri")
st.write("Silakan unggah laporan bulanan perusahaan di bawah ini untuk memproses data secara otomatis.")
st.markdown("---")

# --- AREA UTAMA: KOTAK UPLOAD FILE ---
col_up1, col_up2, col_up3 = st.columns([1, 2, 1])

with col_up2:
    uploaded_file = st.file_uploader(
        "📂 Tarik atau Pilih File Laporan Bulanan (.xlsx / .csv)", 
        type=["xlsx", "csv"],
        help="Format file harus berisikan kolom data Material Request"
    )

# Cek apakah file sudah diunggah ke sistem
if uploaded_file is not None:
    # --- MEMBACA DATA ---
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # --- PERBAIKAN TOTAL: MENGISI SEL KOSONG / MERGED CELL MENYELURUH ---
    df = df.ffill()
    # -------------------------------------------------------------------
    
    st.success("Berhasil! Laporan bulanan telah terbaca oleh sistem.")
    
    # --- 1. PEMBERSIHAN & PENGOLAHAN DATA ---
    # Mengisi missing value Qty dengan median (sesuai revisi penguji)
    if 'Qty' in df.columns:
        median_qty = df['Qty'].median()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(median_qty)
    
    # Hitung Jarak Waktu (Lead Time) otomatis
    if 'MR Date' in df.columns and 'Tgl Penyerahan' in df.columns:
        df['MR Date'] = pd.to_datetime(df['MR Date'], errors='coerce')
        df['Tgl Penyerahan'] = pd.to_datetime(df['Tgl Penyerahan'], errors='coerce')
        df['Lead_Time'] = (df['Tgl Penyerahan'] - df['MR Date']).dt.days
        
        def label_kategori(val):
            if pd.isna(val):
                return 'Tidak Valid'
            elif val <= 1:
                return 'Cepat'
            elif val <= 3:
                return 'Standar'
            else:
                return 'Lambat'
        df['Kategori_Waktu'] = df['Lead_Time'].apply(label_kategori)

    st.markdown("---")

    # --- 2. MENU FILTER INTERAKTIF DI DASHBOARD UTAMA ---
    st.subheader("Filter & Kontrol Data")
    if 'Kategori_Waktu' in df.columns:
        status_opsi = df['Kategori_Waktu'].unique()
        selected_status = st.multiselect(
            "Filter berdasarkan Kategori Waktu Pengerjaan:",
            options=status_opsi,
            default=list(status_opsi)
        )
        df_filtered = df[df['Kategori_Waktu'].isin(selected_status)]
    else:
        df_filtered = df

    st.markdown("---")

    # --- 3. RINGKASAN KARTU METRIK OPERASIONAL ---
    st.subheader("Ringkasan Eksekutif Kinerja Gudang")
    m1, m2, m3, m4 = st.columns(4)
    total_req = len(df_filtered)
    avg_lead = f"{df_filtered['Lead_Time'].mean():.1f} Hari" if 'Lead_Time' in df_filtered.columns else "N/A"
    jml_lambat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Lambat']) if 'Kategori_Waktu' in df_filtered.columns else 0
    jml_cepat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Cepat']) if 'Kategori_Waktu' in df_filtered.columns else 0

    m1.metric("Total Permintaan (MR)", total_req)
    m2.metric("Rata-rata Waktu Tunggu", avg_lead)
    m3.metric("Kategori 'Lambat'", jml_lambat)
    m4.metric("Kategori 'Cepat'", jml_cepat)
    
    st.markdown("---")

    # --- 4. TABEL DETAIL DATA & TOMBOL DOWNLOAD ---
    st.subheader("Lembar Data Masuk (Database Viewer)")
    st.dataframe(df_filtered, use_container_width=True)

    # --- FUNGSI PEMBUATAN FILE EKSPOR ---
    col_dl1, col_dl2 = st.columns(2)

    # A. Tombol Download Excel (.xlsx)
    with col_dl1:
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Laporan_Filtered')
        excel_data = output_excel.getvalue()

        st.download_button(
            label="📥 Unduh Data ke Excel (.xlsx)",
            data=excel_data,
            file_name="Laporan_Material_Request_Epsindo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # B. Tombol Download Laporan Ringkasan PDF (.pdf)
    with col_dl2:
        def generate_pdf(total, avg, lambat, cepat):
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1f4e78'),
                spaceAfter=12
            )
            normal_style = styles['Normal']
            
            story.append(Paragraph("Laporan Ringkasan Kinerja Workshop Duri", title_style))
            story.append(Paragraph("PT Epsindo Jaya Pratama", styles['Heading3']))
            story.append(Spacer(1, 12))
            
            data_tabel = [
                ["Metrik Kinerja", "Hasil Analisis"],
                ["Total Permintaan (MR)", str(total)],
                ["Rata-rata Waktu Tunggu", str(avg)],
                ["Jumlah Kategori 'Lambat'", str(lambat)],
                ["Jumlah Kategori 'Cepat'", str(cepat)]
            ]
            
            t = Table(data_tabel, colWidths=[200, 200])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f2f2f2')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
            ]))
            
            story.append(t)
            story.append(Spacer(1, 20))
            story.append(Paragraph("Dokumen ini digenerate secara otomatis oleh Sistem Monitoring Bulanan PT Epsindo.", normal_style))
            
            doc.build(story)
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()

        pdf_bytes = generate_pdf(total_req, avg_lead, jml_lambat, jml_cepat)
        st.download_button(
            label="📄 Unduh Ringkasan Laporan ke PDF",
            data=pdf_bytes,
            file_name="Ringkasan_Laporan_Epsindo.pdf",
            mime="application/pdf"
        )

    st.markdown("---")

    # --- 5. PEMODELAN MACHINE LEARNING (RANDOM FOREST) & EVALUASI ---
    st.subheader("Analisis Prediktif & Evaluasi Model Random Forest")
    
    if 'Qty' in df_filtered.columns and 'Kategori_Waktu' in df_filtered.columns:
        df_model = df_filtered.dropna(subset=['Qty', 'Kategori_Waktu'])
        df_model = df_model[df_model['Kategori_Waktu'] != 'Tidak Valid']
        
        if len(df_model) > 10:
            X = df_model[['Qty']]
            y = df_model['Kategori_Waktu']
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
            rf_model.fit(X_train, y_train)
            y_pred = rf_model.predict(X_test)
            
            # Tampilkan Tingkat Akurasi
            acc = accuracy_score(y_test, y_pred)
            st.info(f"💡 Status Model: Berhasil dilatih secara otomatis menggunakan algoritma Random Forest dengan tingkat akurasi **{acc * 100:.2f}%**")
            
            # Tampilkan Grafik Evaluasi dalam 2 Kolom
            g1, g2 = st.columns(2)
            
            with g1:
                st.write("**Confusion Matrix (Evaluasi Prediksi)**")
                fig_cm, ax_cm = plt.subplots(figsize=(5, 4))
                cm = confusion_matrix(y_test, y_pred, labels=rf_model.classes_)
                disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=rf_model.classes_)
                disp.plot(ax=ax_cm, cmap='Blues', values_format='d')
                st.pyplot(fig_cm)
                
            with g2:
                st.write("**Feature Importance (Variabel Pengaruh)**")
                fig_fi, ax_fi = plt.subplots(figsize=(5, 4))
                feature_importances = rf_model.feature_importances_
                sns.barplot(x=feature_importances, y=X.columns, ax=ax_fi, palette='viridis', hue=X.columns, legend=False)
                ax_fi.set_xlabel("Skor Kepentingan")
                st.pyplot(fig_fi)
        else:
            st.warning("⚠️ Data setelah difilter terlalu sedikit untuk melatih model Random Forest (minimal butuh 10 baris data).")

else:
    # Tampilan awal jika belum ada file yang di-upload
    st.info("**Petunjuk Penggunaan:** Silakan klik kotak unggah di atas atau tarik file laporan Excel/CSV perusahaan ke area tersebut untuk menampilkan sistem evaluasi dan prediksi.")