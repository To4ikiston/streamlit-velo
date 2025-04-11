import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client, Client

# Конфигурация Supabase (замените на свои данные)
SUPABASE_URL = "https://ozuvntvkuzmsuaaniyhr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96dXZudHZrdXptc3VhYW5peWhyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIxMjY3MTksImV4cCI6MjA1NzcwMjcxOX0.EaBAzB5hs7v8wtX5ld6FJl0hmpcquWuIzwU_Rah3Iw0"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Создаем две вкладки: "Новая тренировка" и "Аналитика"
tabs = st.tabs(["Новая тренировка", "Аналитика"])


##########################
# Вкладка "Новая тренировка"
with tabs[0]:
    st.header("Внести новую тренировку")
    with st.form("training_form"):
        st.subheader("Основные данные")
        training_date = st.date_input("Дата тренировки")
        training_time = st.time_input("Время тренировки", value=datetime.now().time())
        training_type = st.selectbox("Тип тренировки", options=["Кардио", "Интервальная", "Силовая", "Другое"])

        st.subheader("Показатели тренировки")
        avg_speed = st.number_input("Средняя скорость (KPH)", min_value=0.0, step=0.1)
        avg_cal_hr = st.number_input("Калорий в час", min_value=0.0, step=0.1)
        avg_min_km = st.number_input("Время на км (мин/км)", min_value=0.0, step=0.1)
        avg_rpm = st.number_input("Обороты в минуту (RPM)", min_value=0.0, step=1.0)
        avg_watts = st.number_input("Средняя мощность (WATTS)", min_value=0.0, step=1.0)
        avg_mets = st.number_input("Показатель METS", min_value=0.0, step=0.1)
        avg_hr = st.number_input("Средний пульс (BPM)", min_value=0.0, step=1.0)
        calories = st.number_input("Сожжённые калории", min_value=0.0, step=1.0)
        distance = st.number_input("Дистанция (км)", min_value=0.0, step=0.1)
        duration = st.number_input("Время тренировки (мин)", min_value=0.0, step=1.0)

        st.subheader("Комментарии")
        comments = st.text_area("Комментарий к тренировке")

        submit_button = st.form_submit_button("Сохранить тренировку")

    if submit_button:
        # Объединяем дату и время в формат ISO
        training_datetime = datetime.combine(training_date, training_time).isoformat()

        data = {
            "training_date": training_datetime,
            "training_type": training_type,
            "avg_speed": avg_speed,
            "avg_cal_hr": avg_cal_hr,
            "avg_min_km": avg_min_km,
            "avg_rpm": avg_rpm,
            "avg_watts": avg_watts,
            "avg_mets": avg_mets,
            "avg_hr": avg_hr,
            "calories": calories,
            "distance": distance,
            "duration": duration,
            "comments": comments
        }

        try:
            result = supabase.table("workouts").insert(data).execute()
            if result.data:
                st.success("Тренировка сохранена успешно!")
            else:
                st.error("Произошла ошибка при сохранении тренировки! Пустой ответ от сервера.")
        except Exception as e:
            st.error(f"Произошла ошибка при сохранении тренировки! Ошибка: {e}")


##########################
# Вкладка "Аналитика"
with tabs[1]:
    st.header("Аналитика тренировок")

    # Заменяем слайдер на number_input, чтобы можно было пользоваться кнопками + и -
    days = st.number_input("Показать данные за последние (дней)", min_value=7, max_value=365, value=30, step=1)

    # Получаем данные из Supabase
    result = supabase.table("workouts").select("*").execute()
    if result.data:
        df = pd.DataFrame(result.data)

        # Преобразуем дату (без устаревшего аргумента infer_datetime_format)
        df['training_date'] = pd.to_datetime(
            df['training_date'],
            utc=True,
            errors='coerce'
        )
        df = df.dropna(subset=['training_date'])

        df = df.sort_values("training_date")

        # Фильтруем по выбранному периоду: от (максимальная дата - days)
        last_date = df['training_date'].max()
        if pd.isna(last_date):
            st.error("Не удалось определить максимальную дату. Возможно, все даты некорректны.")
            st.stop()
        start_date = last_date - pd.Timedelta(days=int(days))
        df_period = df[df['training_date'] >= start_date]
    else:
        st.error("Нет данных для анализа.")
        df_period = None

    if df_period is not None and not df_period.empty:
        # 1. Комплексный сравнительный анализ (Радиальная диаграмма)

        st.subheader("1. Комплексный сравнительный анализ (Радиальная диаграмма)")

        # Список интересующих метрик
        metrics_cols = ["avg_speed", "avg_watts", "avg_hr", "distance", "calories"]

        # Вычислим средние по выбранному периоду
        metrics_mean = {col: df_period[col].mean() for col in metrics_cols}

        # Найдем min и max по каждой метрике для нормализации
        scaled_metrics = {}
        for col in metrics_cols:
            col_min = df_period[col].min()
            col_max = df_period[col].max()
            col_val = metrics_mean[col]

            if col_max > col_min:
                scaled_val = (col_val - col_min) / (col_max - col_min)
            else:
                # Случай, когда min и max совпадают – нет разброса значений
                scaled_val = 0.5  # По вашему выбору

            # Если это средний пульс (avg_hr), инвертируем
            if col == "avg_hr":
                scaled_val = 1 - scaled_val

            scaled_metrics[col] = scaled_val

        categories = list(scaled_metrics.keys())
        values = list(scaled_metrics.values())

        # Замыкаем круг
        values += values[:1]
        categories += categories[:1]

        fig_radar = go.Figure(
            data=[
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name='Нормированные показатели'
                )
            ],
            layout=go.Layout(
                polar=dict(radialaxis=dict(visible=True)),
                showlegend=False,
                title="Нормированные средние показатели"
            )
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        with st.expander("Интерпретация"):
            st.write(
                """На данной радиальной диаграмме мы используем **min-max нормализацию**, 
чтобы привести каждую метрику к диапазону [0..1]. Это исключает ситуацию, при которой одна метрика 
(например, калории с большими абсолютными значениями) «забивает» остальные.

**Алгоритм min-max**:
\[
\text{scaled} = \frac{\text{value} - \text{min}}{\text{max} - \text{min}}
\]

Если \(\text{max} = \text{min}\), тогда отсутствует разброс значений, и мы ставим им все 0.5 (или любое фиксированное значение).

Для **среднего пульса (avg_hr)** мы делаем инверсию результата (1 - scaled), 
так как **снижение** пульса при одинаковых нагрузках считается улучшением.

**Итог**: 
- Чем больше радиус по показателям скорости, мощности, дистанции и калорий, тем лучше.
- Чем ближе радиус к внешнему кругу по “avg_hr”, тем ниже пульс, что считается положительным признаком адаптации сердца."""  
            )

        # 2. Адаптация сердечно-сосудистой системы
        st.subheader("2. Адаптация сердечно-сосудистой системы")
        fig2_line = px.line(df_period, x="training_date", y="avg_hr", title="Динамика среднего пульса (avg_hr)", markers=True)
        st.plotly_chart(fig2_line, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Этот график демонстрирует изменение среднего пульса по датам.
Если пульс при увеличении нагрузки остается стабильным или снижается, значит ваше сердце становится более выносливым."""
            )

        st.subheader("Пульс vs Мощность")
        fig2_scatter1 = px.scatter(df_period, x="avg_watts", y="avg_hr", title="Пульс (avg_hr) vs Мощность (avg_watts)", trendline="ols")
        st.plotly_chart(fig2_scatter1, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Этот scatter-plot показывает зависимость между мощностью и пульсом.
Умеренный рост пульса при росте мощности говорит о нормальной адаптации сердечно-сосудистой системы."""
            )

        st.subheader("Пульс vs Калории в час")
        fig2_scatter2 = px.scatter(df_period, x="avg_cal_hr", y="avg_hr", title="Пульс (avg_hr) vs Калории/час (avg_cal_hr)", trendline="ols")
        st.plotly_chart(fig2_scatter2, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Сравнение пульса и калорий в час показывает, насколько ваше сердце отвечает на рост энергозатрат.
Балансированный рост обоих параметров говорит о корректной тренировочной нагрузке."""
            )

        # 3. Развитие выносливости
        st.subheader("3. Развитие выносливости")
        fig3_line = px.line(df_period, x="training_date", y="avg_speed", title="Динамика средней скорости (avg_speed)", markers=True)
        st.plotly_chart(fig3_line, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Средняя скорость (avg_speed) – ключевой показатель выносливости.
Если она повышается при аналогичном или меньшем времени тренировки, значит ваш уровень физической подготовки растет."""
            )

        st.subheader("Дистанция и Время тренировок")
        fig3_dual = go.Figure()
        fig3_dual.add_trace(
            go.Bar(x=df_period['training_date'], y=df_period['distance'], name='Дистанция (км)', marker_color='indianred')
        )
        fig3_dual.add_trace(
            go.Scatter(x=df_period['training_date'], y=df_period['duration'], name='Время (мин)',
                       mode='lines+markers', yaxis='y2', line=dict(color='royalblue'))
        )
        fig3_dual.update_layout(
            title="Дистанция и Время тренировок",
            xaxis=dict(title="Дата тренировки"),
            yaxis=dict(title="Дистанция (км)"),
            yaxis2=dict(title="Время (мин)", overlaying='y', side='right'),
            legend=dict(x=0, y=1.1, orientation="h")
        )
        st.plotly_chart(fig3_dual, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Этот комбинированный график показывает, как меняется дистанция и время тренировки.
Если дистанция увеличивается, а время остаётся таким же или уменьшается, это свидетельствует об улучшении выносливости."""
            )

        # 4. Энергетические затраты
        st.subheader("4. Энергетические затраты")
        fig4_line = px.line(df_period, x="training_date", y="calories", title="Динамика сожжённых калорий", markers=True)
        st.plotly_chart(fig4_line, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Этот график показывает, как изменяется количество сожжённых калорий.
Если калорийная отдача растёт вместе с интенсивностью, значит организм эффективно расходует энергию."""
            )

        st.subheader("Показатель METS")
        fig4_line2 = px.line(df_period, x="training_date", y="avg_mets", title="Динамика METS", markers=True)
        st.plotly_chart(fig4_line2, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """METS – показатель энергетической затратности тренировки.
Рост METS параллельно с увеличением сожжённых калорий указывает на повышение интенсивности занятий."""
            )

        st.subheader("Длительность vs Сожжённые калории")
        fig4_scatter = px.scatter(df_period, x="duration", y="calories", title="Длительность тренировки vs Сожжённые калории", trendline="ols")
        st.plotly_chart(fig4_scatter, use_container_width=True)
        with st.expander("Интерпретация"):
            st.write(
                """Этот scatter-plot иллюстрирует, как связаны длительность тренировки и общее количество сожжённых калорий.
Помогает понять, растёт ли расход энергии при увеличении времени."""
            )
    else:
        st.write("Нет данных для отображения графиков.")
