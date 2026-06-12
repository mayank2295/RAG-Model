const router = require('express').Router();
const { getSettlements, createSettlement } = require('../controllers/settlementController');
const auth = require('../middleware/auth');

router.get('/:id/settlements', auth, getSettlements);
router.post('/:id/settlements', auth, createSettlement);

module.exports = router;
