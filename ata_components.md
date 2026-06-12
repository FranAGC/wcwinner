# Algoritmo Genético: Sintonización Adaptativa (ATA)

El sistema de Predicción Paralela (WC26_SIM) utiliza un modelo de Machine Learning basado en un **Algoritmo Genético**. Este documento sirve como guía para entender, mejorar o corregir sus componentes en el futuro.

## 1. El Entorno de Competición
El algoritmo no altera la base de datos oficial (`WC26`). En su lugar, opera sobre una dimensión paralela aislada: `WC26_SIM`. 
Esto permite que el sistema evalúe "qué pasaría si..." sin afectar el avance del torneo real.

## 2. Los Cromosomas (Pesos/Genes)
En el motor ATA (ubicado en `backend/services/probability.py`), las decisiones no tienen un peso estático. Existen 6 "genes" paramétricos (todos inicializan en `1.0`) que el algoritmo genético altera para "mutar" la forma en que se predicen los goles:

1. `w_elo`: Ponderación de la diferencia del ranking ELO histórico.
2. `w_att`: Relevancia del balance entre Fuerzas de Ataque vs Fuerzas de Defensa.
3. `w_form`: Ponderación de la forma o racha reciente de victorias de los equipos.
4. `w_h2h`: Relevancia de los enfrentamientos previos directos (Head-to-Head).
5. `w_squad`: Ponderación del tamaño/calidad de la convocatoria (`squad_calls`).
6. `w_rating`: Impacto del nivel individual de los jugadores (`players`).

## 3. Función de Aptitud (Fitness / Loss Function)
Ubicación: `backend/services/ml_optimizer.py -> _calculate_fitness()`

¿Cómo sabe el algoritmo si una mutación es buena o mala? 
Utiliza el **Error Absoluto Medio (MAE)** enfocado en la predicción de Goles.
1. Toma un partido real que ya haya concluido en el torneo oficial (`WC26`).
2. Genera una predicción usando los genes actuales.
3. Compara: `|goles_predichos - goles_reales|`.
4. El objetivo del algoritmo es "Sobrevivir" acercando ese margen de error a **0.0**.

## 4. Proceso Evolutivo (Crossover & Mutación)
Al presionar "Entrenar Algoritmo", se dispara el endpoint `/algorithm/optimize`:
- **Población:** Crea múltiples variaciones de los pesos (ej. 10 simuladores virtuales).
- **Selección:** Los 5 que obtuvieron el menor margen de error (MAE) sobreviven.
- **Crossover (Cruce):** Los sobrevivientes mezclan sus genes (promediando sus pesos) para crear una nueva generación.
- **Mutación:** Existe un 10% de probabilidad de que un gen cambie aleatoriamente de valor (saltos cuánticos) para evitar quedarse atrapado en un mínimo local matemático.

## Posibles Mejoras a Futuro
- **Función de Pérdida Mixta:** Cambiar el MAE por un "Log-Loss", que penalice más fuerte cuando el sistema predice 99% de victoria y el equipo termina perdiendo.
- **Genes Climáticos:** Agregar un gen `w_climate` si en el futuro se incorpora la tabla de factores climáticos en los estadios.
