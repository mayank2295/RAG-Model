const router = require('express').Router();
const { searchUsers, getMyBalances } = require('../controllers/userController');
const auth = require('../middleware/auth');

router.get('/search', auth, searchUsers);
router.get('/me/balances', auth, getMyBalances);

module.exports = router;
