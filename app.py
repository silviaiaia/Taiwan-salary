import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="薪資結構統計", layout="wide")

st.title("薪資結構統計")

st.sidebar.header("資料上傳")
uploaded_file = st.sidebar.file_uploader("請上傳 Excel 檔案", type=['xlsx', 'xls'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    try:
        if df['Monthly_Salary'].dtype == 'object':
            df['Monthly_Salary'] = df['Monthly_Salary'].astype(str).str.replace(',', '').astype(float)

        df['Year'] = df['Year'].astype(int)

        df = df.dropna(subset=['Monthly_Salary', 'Job_Title', 'Year'])
        
    except Exception as e:
        st.error(f"資料格式錯誤：{str(e)}")
        st.info("請確認 Excel 檔案中：\n- Monthly_Salary 欄位為數字\n- Year 欄位為年份\n- Job_Title 欄位為文字")
        st.stop()

    st.sidebar.header("篩選條件")
    st.sidebar.markdown("---")

    years = sorted(df['Year'].unique())
    selected_years = st.sidebar.multiselect(
        "選擇年份",
        options=years,
        default=years
    )

    job_titles = sorted(df['Job_Title'].unique())
    selected_jobs = st.sidebar.multiselect(
        "選擇職位",
        options=job_titles,
        default=job_titles
    )

    filtered_df = df[
        (df['Year'].isin(selected_years)) & 
        (df['Job_Title'].isin(selected_jobs))
    ]

    st.subheader("資料概覽")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("總筆數", len(df))
    with col2:
        st.metric("平均月薪", f"${df['Monthly_Salary'].mean():,.0f}")
    with col3:
        st.metric("職位數量", df['Job_Title'].nunique())
    with col4:
        st.metric("最低薪資", f"${filtered_df['Monthly_Salary'].min():,.0f}")
    with col5:
        st.metric("最高薪資", f"${filtered_df['Monthly_Salary'].max():,.0f}")

    st.subheader("統計摘要")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("P10", f"${filtered_df['Monthly_Salary'].quantile(0.10):,.0f}")
    with col2:
        st.metric("P25", f"${filtered_df['Monthly_Salary'].quantile(0.25):,.0f}")
    with col3:
        st.metric("P50 中位數", f"${filtered_df['Monthly_Salary'].median():,.0f}")
    with col4:
        st.metric("P75", f"${filtered_df['Monthly_Salary'].quantile(0.75):,.0f}")
    with col5:
        st.metric("P90", f"${filtered_df['Monthly_Salary'].quantile(0.90):,.0f}")
    
    
    if len(filtered_df) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("薪資分布直方圖")
            fig_hist = px.histogram(
                filtered_df,
                x='Monthly_Salary',
                nbins=30,
                title='月薪分布',
                labels={'Monthly_Salary': '月薪', 'count': '人數'}
            )
            fig_hist.update_layout(showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            st.subheader("薪資箱型圖")
            fig_box = px.box(
                filtered_df,
                y='Monthly_Salary',
                title='薪資分布箱型圖',
                labels={'Monthly_Salary': '月薪'}
            )
            st.plotly_chart(fig_box, use_container_width=True)

        st.subheader("各職位平均薪資")
        job_salary = filtered_df.groupby('Job_Title')['Monthly_Salary'].agg(['mean', 'count']).reset_index()
        job_salary.columns = ['職位', '平均月薪', '樣本數']
        job_salary = job_salary.sort_values('平均月薪', ascending=False)
        
        fig_bar = px.bar(
            job_salary,
            x='職位',
            y='平均月薪',
            title='各職位平均月薪比較',
            text='平均月薪',
            hover_data=['樣本數']
        )
        fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_bar.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("年度薪資趨勢")
        yearly_salary = filtered_df.groupby('Year')['Monthly_Salary'].mean().reset_index()
        
        fig_line = px.line(
            yearly_salary,
            x='Year',
            y='Monthly_Salary',
            title='歷年平均月薪趨勢',
            labels={'Year': '年份', 'Monthly_Salary': '平均月薪'},
            markers=True
        )
        st.plotly_chart(fig_line, use_container_width=True)

        with st.expander("查看原始資料"):
            st.dataframe(df, use_container_width=True)
        
    else:
        st.warning("沒有符合篩選條件的資料，請調整篩選條件。")
else:
    st.info("請上傳 Excel 檔案以開始分析")