<!-- frontend-cdn/components/StarRating.vue -->
<template>
  <div class="star-rating">
    <span
      v-for="score in 10"
      :key="score"
      @click="handleClick(score)"
      :class="{active: currentScore >= score}"
    >★</span>
  </div>
</template>

<script>
export default {
  props: {
    // 接收父组件传的当前评分
    currentScore: {
      type: Number,
      default: 0
    }
  },
  methods: {
    handleClick(score) {
      // 点击后把评分传给父组件
      this.$emit('score-change', score);
    }
  }
}
</script>

<style scoped>
/* 这里复用之前的star.css样式 */
.star-rating {
  color: #ccc;
  font-size: 20px;
  margin: 10px 0;
}
.star-rating span {
  cursor: pointer;
}
.star-rating span.active {
  color: #ffc107;
}
</style>