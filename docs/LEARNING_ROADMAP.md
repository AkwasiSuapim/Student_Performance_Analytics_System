# Guided Learning Roadmap

The codebase is complete enough to run, but the learning process should still move layer by layer. Do not try to memorize the files. Learn the decisions that connect them.

## Phase 1 — Python and OOP foundation

Study `models/student.py`.

Be able to explain:

- Why a class is useful here.
- The difference between an attribute and a method.
- Why grades use a dictionary.
- What `__post_init__` validates.
- How `get_average` and `get_grade_letter` work.

Exercise: create one student in the Python shell, add a grade, and calculate the new average.

## Phase 2 — Composition and statistics

Study `models/course.py`.

Be able to derive the mean, median, variance, standard deviation, and pass-rate formulas by hand. Then connect each formula to its method.

Exercise: calculate a three-student class average manually and verify the program's result.

## Phase 3 — Data pipelines

Study `data_io.py`.

Trace one CSV row through validation, dictionary construction, the `Student` constructor, and the `Course` collection.

Exercise: deliberately enter an attendance rate of 110 and explain where and why the program rejects it.

## Phase 4 — Explainable analysis

Study `analytics/risk.py` and `analytics/statistics.py`.

Challenge the rules. Ask whether an indicator is fair, useful, measurable, and actionable. A support flag should help start a conversation, not replace one.

Exercise: change one threshold and predict which students will move between risk levels before rerunning the analysis.

## Phase 5 — Visualization and reporting

Study `visualization.py` and `reporting.py`.

For each chart, identify the question it answers. Remove any chart that does not support a real decision.

Exercise: write a two-sentence interpretation of the attendance scatter plot without claiming that attendance causes grades.

## Phase 6 — Machine learning

Study `ml.py` only after the earlier phases are clear.

Learn:

- Feature versus target.
- Training versus testing data.
- Data leakage.
- Linear regression versus random forest.
- MAE, RMSE, and R².
- Why a synthetic demonstration cannot justify real interventions.

Exercise: calculate one absolute prediction error by hand, then relate it to MAE.

## Phase 7 — Portfolio and product development

After the engine is understood and tested:

1. Replace synthetic data with an approved anonymized dataset.
2. Add a Streamlit dashboard in Python.
3. Add persistent storage.
4. Add user roles only if a real use case requires them.
5. Add model validation and bias audits.
6. Deploy a safe public demonstration using synthetic data.

