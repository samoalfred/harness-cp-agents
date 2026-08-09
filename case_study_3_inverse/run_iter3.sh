#!/bin/bash
export LD_LIBRARY_PATH=/home/samoalfred/dealii-candi/symengine-0.8.1/lib:$LD_LIBRARY_PATH
cd /home/samoalfred/candi/plasticity/applications/crystalPlasticity/fcc/Cu_REACT_Inverse2
rm -f run_iter3.log
python3.7 run_iter3.py > run_iter3.log 2>&1
echo "EXIT=$?" >> run_iter3.log
