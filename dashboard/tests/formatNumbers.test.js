import test from 'node:test';
import assert from 'node:assert/strict';
import { axisNumber } from '../src/services/formatNumbers.js';

test('Trục số dùng nghìn/triệu và dấu phẩy thập phân theo tiếng Việt', () => {
  assert.equal(axisNumber(500), '500');
  assert.equal(axisNumber(1500), '1,5 nghìn');
  assert.equal(axisNumber(20000), '20 nghìn');
  assert.equal(axisNumber(1500000), '1,5 triệu');
});
