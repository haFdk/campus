<template>
  <el-result icon="info" title="页面不存在" sub-title="这个地址已停用，去看看校园里的闲置好物吧。">
    <template #extra><el-button type="primary" @click="$router.push('/items')">浏览闲置</el-button></template>
  </el-result>
</template>
