<template>
  <article class="navbar">
    <div>
      <img src="/logo.png" alt="SSHManager logo" class="logo">
      <sub class="version">2022</sub>
    </div>

    <div>
      <a href="/api/debug-zip" download="debug.zip" data-tooltip="Tải file thông tin debug" target="_blank"
         role="button"
         class="outline"><i class="fi fi-bug"/></a>
      <a href="https://facebook.com/kenhanhgia" data-tooltip="Facebook" target="_blank" role="button"
         class="outline"><i class="fi fi-facebook"/></a>
      <a href="https://t.me/kenhanhgia" data-tooltip="Zalo" target="_blank" role="button"
         class="outline"><i class="fi fi-comment"/></a>
    </div>
  </article>
</template>

<script>
export default {
  name: "NavBar",
  props: {
    version: String,
  },
}
</script>

<style lang="scss" scoped>
.navbar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: auto;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;

  & > * {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .logo {
    border-radius: var(--border-radius);
    box-shadow: var(--card-box-shadow);
  }

  .version {
    width: 100%;
    text-align: center;
  }

  a[role=button], button {
    width: 100%;
  }

  .donate {
    --primary: #ff365b;
    --primary-focus: rgba(255, 54, 91, 0.2);
    --primary-hover: #d92b4b;
  }
}
</style>