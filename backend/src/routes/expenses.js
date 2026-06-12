const router = require('express').Router();
const { getExpense, updateExpense, deleteExpense } = require('../controllers/expenseController');
const auth = require('../middleware/auth');

router.get('/:id', auth, getExpense);
router.put('/:id', auth, updateExpense);
router.delete('/:id', auth, deleteExpense);

module.exports = router;
