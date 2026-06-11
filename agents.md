# Historial y Contexto de Agentes AI (WC Winner 2026)

Este archivo (`agents.md`) sirve como manifiesto y contexto acumulativo para futuros agentes de IA o desarrolladores que interactúen con el código base. Resume el estado, las decisiones arquitectónicas y los pendientes del proyecto.

## 🎯 Meta del Proyecto
Desarrollar un motor probabilístico y simulador web completo para la Copa Mundial de Fútbol 2026, abarcando desde la fase de grupos de 48 equipos hasta la Gran Final, fundamentado en resultados reales recopilados por la comunidad de código abierto, implementando distribuciones de Poisson y sistema de puntaje ELO con decaimiento temporal.

## ⚙️ Stack Tecnológico
- **Base de Datos**: DuckDB (Alto rendimiento, enfocado en agregaciones y procesamiento OLAP). *Nota*: Se han omitido temporalmente los `FOREIGN KEYS` para agilizar los procesos masivos de Upsert.
- **Backend**: FastAPI (Python). Procesamiento de datos con `Polars` y `Numpy`.
- **Frontend**: React.js, Vite, TypeScript, UI construida con "Glassmorphism", diseño oscuro de alta tecnología, y componentes responsivos. 

## 🗺️ Logros y Funcionalidades Construidas
1. **Pipeline de Ingestión de Datos (ETL)**:
   - Capacidad de restaurar la base de datos completamente de forma local mediante respaldos CSV (`backend/data/`).
   - Cálculo estático en masa de fuerzas estadísticas de ataque/defensa (`attack_strength`, `defense_strength`) con ponderación temporal (decay_half_life).
2. **Motor de Predicción Poisson**:
   - Predicción multivariable integrada en la base de datos local. Generación de la probabilidad porcentual para victorias, empates y derrotas.
3. **Simulación Estructurada del Torneo (WC26)**:
   - Soporte nativo para 12 Grupos (A al L), la regla oficial de "mejores terceros", y la correcta asignación de enfrentamientos en el Bracket de 32 equipos.
   - API con endpoints progresivos para avanzar las rondas (Grupos -> 16avos -> Octavos -> Cuartos -> Semis -> Final).
4. **Reseteo del Entorno**:
   - `seed_wc26.py`: Restablece el árbol de simulación en microsegundos, para un flujo iterativo rápido en el frontend.
   - `run_etl.py`: Limpia la BD completamente y la restaura desde los archivos CSV locales (sin conexión a internet).

## 🚧 Tareas Pendientes / Consideraciones Futuras
1. **Variables Geográficas/Climáticas**: A futuro, el modelo debería incorporar el clima y la altitud de las ciudades anfitrionas en la distribución Poisson (Estados Unidos, México, Canadá) como ponderadores adicionales (fuerza de cansancio o factor local amplificado).
2. **Animaciones Visuales**: Mejorar las transiciones del `TournamentBracket` al momento de presionar "Simular" de manera secuencial (animando los cruces uno a uno).
3. **Optimización de Memoria**: Actualmente DuckDB se mantiene en `read_only=False` durante interacciones del ETL, lo que puede causar conflictos (IO Error) si otras herramientas visuales como DBeaver se mantienen abiertas concurrentemente.

## 📝 Reglas de Interacción para Futuros Agentes
- **Aesthetic First**: Las actualizaciones de la interfaz deben mantener obligatoriamente el diseño "Glass", usando colores `neon`, `cyan`, `gold` con fondos `blur` para mantener el efecto Premium.
- **Performance**: Cualquier consulta a DuckDB que requiera más de 5,000 registros debe enviarse procesada por Polars para inserción masiva (`executemany` u operaciones vectorizadas). Evitar iteraciones en crudo.
- Al modificar la configuración del torneo WC26, usar el script `backend/scripts/seed_wc26.py` para asegurar que se conserven los 72 partidos de la Fase de Grupos oficiales.
