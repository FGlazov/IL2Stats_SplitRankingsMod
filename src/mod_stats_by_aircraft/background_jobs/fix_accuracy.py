from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket
from ..aircraft_stats_compute import decrement_ammo_bugged, get_sortie_type


class FixAccuracy(BackgroundJob):
    """
    Versions before 1.3.0 counted all bullet/bomb/rocket hits and misses towards stats from all sorties. This was
    incorrect behaviour, since game logs contain bugs in certain cases.

    This job goes through all the sorties that were processed, and decrements the broken sorties.
    """

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__fixed_accuracy=False,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id'))

    def compute_for_sortie(self, sortie):
        # TODO: Refactor this "get all buckets code" into a util function.
        buckets = [(AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                         filter_type='NO_FILTER', player=None))[0],
                   (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                         filter_type='NO_FILTER', player=sortie.player))[0]]
        filter_type = get_sortie_type(sortie)
        if filter_type != 'NO_FILTER':
            buckets.append((AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                 filter_type=filter_type, player=None))[0])
            buckets.append((AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                 filter_type=filter_type, player=sortie.player))[0])

        for bucket in buckets:
            decrement_ammo_bugged(bucket, sortie)
            bucket.update_derived_fields()
            bucket.save()

        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.fixed_accuracy = True
        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.save()

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Fixing accuracy stats. {} sorties left to process.' .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed fixing accuracy stats.'
