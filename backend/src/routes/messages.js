const router = require('express').Router();
const { getMessages } = require('../controllers/messageController');
const auth = require('../middleware/auth');

router.get('/:id/messages', auth, getMessages);

module.exports = router;
