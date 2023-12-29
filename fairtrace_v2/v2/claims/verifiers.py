from shapely.geometry import Point
from shapely.geometry import Polygon
from v2.supply_chains.constants import NODE_TYPE_FARM

GUJI_REGION = [
    [5.77798, 39.46729],
    [5.79087, 39.45859],
    [5.83229, 39.44588],
    [5.86702, 39.44325],
    [5.8925, 39.45552],
    [5.90837, 39.45237],
    [5.93324, 39.44304],
    [5.9496, 39.43185],
    [5.97264, 39.41655],
    [6.00192, 39.39277],
    [6.02568, 39.37081],
    [6.0538, 39.3507],
    [6.08095, 39.34621],
    [6.10905, 39.33529],
    [6.14699, 39.33614],
    [6.18613, 39.32319],
    [6.22672, 39.29187],
    [6.26822, 39.26215],
    [6.28996, 39.22982],
    [6.29445, 39.22078],
    [6.30386, 39.20183],
    [6.31773, 39.18257],
    [6.33345, 39.16101],
    [6.33484, 39.15849],
    [6.34011, 39.13037],
    [6.32615, 39.12935],
    [6.30346, 39.12336],
    [6.29224, 39.11348],
    [6.2753, 39.09441],
    [6.25628, 39.08957],
    [6.23816, 39.09759],
    [6.2228, 39.10331],
    [6.20652, 39.1072],
    [6.18084, 39.11682],
    [6.17028, 39.13402],
    [6.16294, 39.13585],
    [6.16228, 39.10693],
    [6.15794, 39.08375],
    [6.15085, 39.05965],
    [6.14238, 39.03852],
    [6.14721, 39.01535],
    [6.15204, 38.99216],
    [6.16421, 38.96462],
    [6.18531, 38.95407],
    [6.19684, 38.94625],
    [6.20526, 38.94054],
    [6.22523, 38.9295],
    [6.23348, 38.92494],
    [6.26353, 38.90177],
    [6.28968, 38.88961],
    [6.30574, 38.87814],
    [6.32525, 38.85656],
    [6.34727, 38.8382],
    [6.36082, 38.81615],
    [6.37872, 38.79825],
    [6.39295, 38.78746],
    [6.40465, 38.77552],
    [6.4081, 38.7705],
    [6.41475, 38.76082],
    [6.41385, 38.74267],
    [6.40193, 38.72152],
    [6.39735, 38.71118],
    [6.40607, 38.69993],
    [6.41066, 38.69556],
    [6.41158, 38.69373],
    [6.41388, 38.67603],
    [6.42397, 38.66547],
    [6.4288, 38.65122],
    [6.42192, 38.63076],
    [6.42813, 38.60893],
    [6.4419, 38.58733],
    [6.44534, 38.57056],
    [6.44168, 38.54412],
    [6.44168, 38.53907],
    [6.44123, 38.5078],
    [6.43527, 38.4793],
    [6.42726, 38.46655],
    [6.42241, 38.45884],
    [6.41025, 38.44505],
    [6.3896, 38.4308],
    [6.37032, 38.42942],
    [6.36105, 38.4269],
    [6.35425, 38.42506],
    [6.32993, 38.42713],
    [6.31088, 38.42851],
    [6.30445, 38.43104],
    [6.29435, 38.42898],
    [6.2698, 38.43657],
    [6.24478, 38.43956],
    [6.22115, 38.44256],
    [6.20301, 38.43843],
    [6.19406, 38.41729],
    [6.1867, 38.39823],
    [6.16925, 38.38077],
    [6.14491, 38.36769],
    [6.12449, 38.36609],
    [6.10826, 38.3587],
    [6.10084, 38.35531],
    [6.07976, 38.34103],
    [6.07677, 38.34567],
    [6.07537, 38.35672],
    [6.06406, 38.37396],
    [6.05159, 38.39027],
    [6.04488, 38.41051],
    [6.03332, 38.43328],
    [6.01579, 38.45096],
    [6.00034, 38.46312],
    [5.98375, 38.46631],
    [5.9644, 38.47018],
    [5.94711, 38.47935],
    [5.92869, 38.4777],
    [5.91418, 38.47192],
    [5.8992, 38.47925],
    [5.87871, 38.47759],
    [5.85935, 38.48584],
    [5.84111, 38.51203],
    [5.82749, 38.53616],
    [5.82009, 38.55523],
    [5.81847, 38.55914],
    [5.81017, 38.56717],
    [5.80525, 38.57019],
    [5.79749, 38.57497],
    [5.78389, 38.58874],
    [5.76107, 38.60272],
    [5.73573, 38.60911],
    [5.70002, 38.62099],
    [5.6749, 38.63543],
    [5.65831, 38.64689],
    [5.63848, 38.66341],
    [5.61749, 38.69418],
    [5.60848, 38.71508],
    [5.5882, 38.72882],
    [5.55342, 38.7414],
    [5.51819, 38.74593],
    [5.49679, 38.7367],
    [5.483, 38.7176],
    [5.4646, 38.70148],
    [5.43997, 38.70305],
    [5.40795, 38.7177],
    [5.38099, 38.7365],
    [5.35933, 38.75921],
    [5.33399, 38.77365],
    [5.31442, 38.77591],
    [5.30451, 38.79244],
    [5.30035, 38.80737],
    [5.28376, 38.82365],
    [5.26188, 38.82867],
    [5.24599, 38.83668],
    [5.22413, 38.83343],
    [5.20917, 38.82882],
    [5.19144, 38.8343],
    [5.1896, 38.83315],
    [5.17763, 38.83773],
    [5.16127, 38.85309],
    [5.14261, 38.87029],
    [5.12879, 38.88611],
    [5.12118, 38.89942],
    [5.11416, 38.90774],
    [5.11151, 38.91088],
    [5.12783, 38.93272],
    [5.14091, 38.96947],
    [5.1296, 38.99953],
    [5.1075, 39.01235],
    [5.08033, 39.03022],
    [5.06259, 39.05475],
    [5.05729, 39.0653],
    [5.05452, 39.06874],
    [5.04991, 39.08089],
    [5.04852, 39.08801],
    [5.04857, 39.10804],
    [5.03009, 39.11116],
    [5.00937, 39.12214],
    [5.0004, 39.12626],
    [4.98658, 39.13541],
    [4.95965, 39.15029],
    [4.93018, 39.17433],
    [4.9067, 39.19288],
    [4.88874, 39.21832],
    [4.87629, 39.24789],
    [4.87097, 39.27426],
    [4.87348, 39.30133],
    [4.86793, 39.327],
    [4.85157, 39.35427],
    [4.8311, 39.36433],
    [4.80626, 39.36635],
    [4.78004, 39.37159],
    [4.76278, 39.38807],
    [4.74229, 39.41165],
    [4.72732, 39.43731],
    [4.72752, 39.46986],
    [4.72979, 39.49828],
    [4.72332, 39.52647],
    [4.71757, 39.53838],
    [4.7125, 39.54914],
    [4.70189, 39.57708],
    [4.68532, 39.59722],
    [4.68116, 39.62104],
    [4.6655, 39.64324],
    [4.65927, 39.66477],
    [4.66912, 39.6948],
    [4.68496, 39.70972],
    [4.69735, 39.72097],
    [4.72441, 39.74588],
    [4.72542, 39.74681],
    [4.72723, 39.74674],
    [4.80482, 39.76169],
    [4.85059, 39.76826],
    [4.89432, 39.78717],
    [4.95521, 39.80764],
    [5.0058, 39.81605],
    [5.0365, 39.83678],
    [5.14404, 39.88158],
    [5.22332, 39.91048],
    [5.2887, 39.94548],
    [5.40048, 40.03687],
    [5.40354, 40.01235],
    [5.39951, 39.98231],
    [5.40743, 39.9452],
    [5.43784, 39.91711],
    [5.47028, 39.89935],
    [5.49403, 39.87353],
    [5.50951, 39.844],
    [5.51929, 39.80391],
    [5.51937, 39.7773],
    [5.51466, 39.74058],
    [5.51246, 39.70594],
    [5.52103, 39.68486],
    [5.55624, 39.66732],
    [5.59044, 39.68074],
    [5.62299, 39.70541],
    [5.64892, 39.7179],
    [5.67883, 39.70677],
    [5.70096, 39.68712],
    [5.719, 39.65139],
    [5.72187, 39.61743],
    [5.71391, 39.58825],
    [5.70208, 39.5501],
    [5.7056, 39.52647],
    [5.72889, 39.50429],
    [5.75908, 39.48006],
    [5.77798, 39.46729],
]


class SystemClaim:
    """Base model for all system claims."""

    def verify(self, batch_criterion):
        """Verification business logic should be implemented in the
        verification subclass for all system claims."""
        raise NotImplementedError()

    @staticmethod
    def get_context():
        """Returns context."""
        return {}


class GoodPriceClaim(SystemClaim):
    """This is not exactly a system claim, but it needs to be marked as
    verified automatically when attached, therefore makind it a system claim
    that always returns true."""

    def verify(self, batch_criterion):
        """Verify with batch criterion."""
        """Currently this is automatically marked as verified.

        The business-logic for this will change later-on
        """
        return True, "Automatically verified as True always.", {}


class TraceableGujiClaim(SystemClaim):
    """This claim checks if the batch originated from a farmer and the farmer
    is from guji region, ie., all the root batches of the batch is owned by a
    farmer and the location of the farmers is inside a preset co-ordinates of
    the guji region."""

    boundary = Polygon(GUJI_REGION)

    def check_point(self, coords):
        """Check point."""
        point = Point(coords)
        return self.boundary.contains(point)

    def verify(self, batch_criterion):
        """Verify with batch criterion."""
        source_region_checks = True
        traceable_checks = True
        farmer_coordinates = []
        info = ""
        _s_transaction = batch_criterion.batch_claim.batch.source_transaction
        root_transactions = _s_transaction.get_root_nodes()
        for transaction in root_transactions:
            # Checking if root is a farm
            n_type = NODE_TYPE_FARM
            is_farm = transaction.externaltransaction.source.type == n_type
            if not is_farm:
                info += (
                    "%s is not a farm. "
                    % transaction.externaltransaction.source.full_name
                )
            traceable_checks &= is_farm

            coordinates = [
                transaction.externaltransaction.source.latitude,
                transaction.externaltransaction.source.longitude,
            ]
            # Checking if root is in Guji region
            source_in_guji = self.check_point(coordinates)
            farmer_coordinates.append(coordinates)
            source_region_checks &= source_in_guji
            if not source_in_guji:
                info += (
                    "%s not in region. "
                    % transaction.externaltransaction.source.full_name
                )
        passed = source_region_checks & traceable_checks
        evidence = {"farmer_coordinates": farmer_coordinates}

        return passed, info, evidence

    @staticmethod
    def get_context():
        """Return context."""
        return {"map_boundary": GUJI_REGION}


class FarmerClaim(SystemClaim):
    """This claim checks if the batch originated from a farmer, ie., all the
    root batches of the batch is owned by a farmer."""

    def verify(self, batch_criterion):
        """Verify with batch criterion."""
        traceable_checks = True
        farmer_coordinates = []
        info = ""
        _s_t = batch_criterion.batch_claim.batch.source_transaction
        root_transactions = _s_t.get_root_nodes()
        for transaction in root_transactions:
            # Checking if root is a farm
            n_type = NODE_TYPE_FARM
            is_farm = transaction.externaltransaction.source.type == n_type
            if not is_farm:
                info += (
                    "%s is not a farm. "
                    % transaction.externaltransaction.source.full_name
                )
            traceable_checks &= is_farm

            coordinates = [
                transaction.externaltransaction.source.latitude,
                transaction.externaltransaction.source.longitude,
            ]
            farmer_coordinates.append(coordinates)
        passed = traceable_checks
        evidence = {"farmer_coordinates": farmer_coordinates}

        return passed, info, evidence
