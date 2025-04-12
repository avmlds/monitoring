from monitoring.task_manager import BaseWorker, Killswitch


def test_killswitch():
    ks = Killswitch()
    assert not ks.engaged
    ks.engage()
    assert ks.engaged


def test_base_worker():
    ks = Killswitch()
    worker = BaseWorker(ks)
    assert worker.killswitch is ks


def test_base_worker_class_name():
    worker = BaseWorker(Killswitch())
    assert worker.class_name() == worker.__class__.__name__
