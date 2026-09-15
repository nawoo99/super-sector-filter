from types import SimpleNamespace
import math
import normal_cpu_gpu_diagnostic as d


def test_cpu_host_denominator_excludes_guest_double_count():
    a=SimpleNamespace(user=0,nice=0,system=0,idle=0,iowait=0,irq=0,softirq=0,steal=0,guest=0)
    b=SimpleNamespace(user=20,nice=0,system=10,idle=65,iowait=5,irq=0,softirq=0,steal=0,guest=8)
    assert d.cpu_busy(a,b)==30


def test_no_elapsed_cpu_time_is_missing_not_zero():
    a=SimpleNamespace(user=1,idle=9)
    assert d.cpu_busy(a,a) is None


def test_distribution_missing_and_nearest_rank():
    assert d.distribution([None,float('nan')])['mean'] is None
    assert d.distribution(range(1,21))==dict(n=20,mean=10.5,p95=19,max=20)


def test_cpu_single_busy_logical_processor_on_twenty():
    idle=SimpleNamespace(user=0,idle=0)
    busy=SimpleNamespace(user=1,idle=0)
    free=SimpleNamespace(user=0,idle=1)
    metrics=[d.cpu_busy(idle,busy)]+[d.cpu_busy(idle,free)]*19
    assert sum(metrics)/20==5
