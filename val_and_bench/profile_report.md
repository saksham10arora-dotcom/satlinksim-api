# Simulation Profile Report

Generated on: 2026-06-06 23:27:46
Steps: 10000
Stations: 4

## Component Runtime Breakdown

| Component    | Runtime | Time (s) |
| ------------ | ------- | -------- |
| Rain Process |   51.0% |   0.0985s |
| Handoff      |   10.3% |   0.0198s |
| SGP4         |    8.3% |   0.0160s |
| Link Budget  |    0.7% |   0.0013s |
| Other        |   29.8% |   0.0575s |

## Top 20 Detailed Stats

```

        1    0.005    0.005    0.193    0.193 /home/satyansh/leo_meo/src/satellite_link_sim.py:351(simulate_all_batched)
        1    0.003    0.003    0.119    0.119 /home/satyansh/leo_meo/src/satellite_link_sim.py:427(<listcomp>)
    10000    0.087    0.000    0.116    0.000 /home/satyansh/leo_meo/src/satellite_link_sim.py:179(step)
    10000    0.008    0.000    0.027    0.000 /home/satyansh/leo_meo/src/satellite_link_sim.py:272(select)
20095/20076    0.011    0.000    0.026    0.000 {built-in method numpy.core._multiarray_umath.implement_array_function}
    10000    0.003    0.000    0.019    0.000 <__array_function__ internals>:177(argmax)
        1    0.005    0.005    0.018    0.018 /home/satyansh/leo_meo/src/propogate.py:172(get_geometry_batch)
    10016    0.004    0.000    0.013    0.000 <__array_function__ internals>:177(where)
    10000    0.005    0.000    0.012    0.000 /home/satyansh/.local/lib/python3.10/site-packages/numpy/core/fromnumeric.py:1153(argmax)
        1    0.010    0.010    0.010    0.010 /home/satyansh/leo_meo/src/satellite_link_sim.py:373(<listcomp>)
    20000    0.010    0.000    0.010    0.000 {method 'rand' of 'numpy.random.mtrand.RandomState' objects}
    10003    0.003    0.000    0.007    0.000 /home/satyansh/.local/lib/python3.10/site-packages/numpy/core/fromnumeric.py:51(_wrapfunc)
    10001    0.007    0.000    0.007    0.000 {method 'normal' of 'numpy.random.mtrand.RandomState' objects}
        1    0.000    0.000    0.006    0.006 /home/satyansh/.local/lib/python3.10/site-packages/sgp4/wrapper.py:8(sgp4_array)
        1    0.006    0.006    0.006    0.006 {method '_sgp4' of 'sgp4.vallado_cpp.Satrec' objects}
        4    0.002    0.000    0.004    0.001 {built-in method builtins.any}
    10000    0.004    0.000    0.004    0.000 /home/satyansh/.local/lib/python3.10/site-packages/sgp4/functions.py:8(jday)
    10000    0.003    0.000    0.003    0.000 {method 'argmax' of 'numpy.ndarray' objects}
    30202    0.003    0.000    0.003    0.000 /home/satyansh/leo_meo/src/satellite_link_sim.py:504(<genexpr>)
       11    0.001    0.000    0.001    0.000 {method 'tolist' of 'numpy.ndarray' objects}


```
