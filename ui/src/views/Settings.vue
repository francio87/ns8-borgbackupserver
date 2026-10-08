<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("settings.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getConfiguration">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-configuration')"
          :description="error.getConfiguration"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-row v-if="fqdn">
            <cv-column>
              <p>
                {{ $t("settings.access_url") }}
                <cv-link :href="bbsUrl" target="_blank">{{ bbsUrl }}</cv-link>
              </p>
            </cv-column>
          </cv-row>
          <cv-form @submit.prevent="saveSettings">
            <NsTextInput
              :label="$t('settings.fqdn')"
              v-model="fqdn"
              placeholder="bbs.example.com"
              :helper-text="$t('settings.fqdn_help')"
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                loading.resetAdminPassword
              "
              :invalid-message="error.fqdn"
              ref="fqdn"
            />
            <NsToggle
              v-model="letsEncrypt"
              :label="$t('settings.lets_encrypt')"
              value="lets-encrypt"
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                loading.resetAdminPassword
              "
            >
              <template slot="text-left">{{ $t("settings.disabled") }}</template>
              <template slot="text-right">{{ $t("settings.enabled") }}</template>
              <template slot="tooltip">{{ $t("settings.tls_help") }}</template>
            </NsToggle>
            <NsTextInput
              :label="$t('settings.ssh_port')"
              v-model="sshPort"
              type="number"
              min="1024"
              max="65535"
              :helper-text="$t('settings.ssh_port_help')"
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                loading.resetAdminPassword
              "
              :invalid-message="error.ssh_port"
              ref="ssh_port"
            />
            <template v-if="!adminPasswordInitialized">
              <p class="bx--form__helper-text">
                {{ $t("settings.admin_password_notice") }}
              </p>
              <NsTextInput
                :label="$t('settings.admin_password')"
                v-model="adminPassword"
                type="password"
                :password-show-label="$t('settings.show_password')"
                :password-hide-label="$t('settings.hide_password')"
                :helper-text="$t('settings.admin_password_help')"
                :disabled="
                  loading.getConfiguration ||
                  loading.configureModule ||
                  loading.resetAdminPassword
                "
                :invalid-message="error.admin_password"
                ref="admin_password"
              />
            </template>
            <cv-accordion v-if="adminPasswordInitialized">
              <cv-accordion-item>
                <template slot="title">{{
                  $t("settings.advanced_options")
                }}</template>
                <template slot="content">
                  <p class="bx--form__helper-text">
                    {{ $t("settings.admin_password_reset_notice") }}
                  </p>
                  <NsInlineNotification
                    v-if="resetPasswordSuccess"
                    kind="success"
                    :title="$t('action.reset-admin-password')"
                    :description="
                      $t(
                        resetPasswordSuccessTwoFactor
                          ? 'settings.admin_password_reset_success_2fa'
                          : 'settings.admin_password_reset_success'
                      )
                    "
                    :showCloseButton="false"
                  />
                  <NsInlineNotification
                    v-if="error.resetAdminPassword"
                    kind="error"
                    :title="$t('action.reset-admin-password')"
                    :description="error.resetAdminPassword"
                    :showCloseButton="false"
                  />
                  <NsButton
                    v-if="!editingAdminPassword"
                    kind="secondary"
                    type="button"
                    :disabled="
                      loading.getConfiguration ||
                      loading.configureModule ||
                      loading.resetAdminPassword
                    "
                    @click="beginAdminPasswordEdit"
                  >
                    {{ $t("settings.modify_admin_password") }}
                  </NsButton>
                  <div v-else>
                    <NsTextInput
                      :label="$t('settings.new_admin_password')"
                      v-model="adminPassword"
                      type="password"
                      :password-show-label="$t('settings.show_password')"
                      :password-hide-label="$t('settings.hide_password')"
                      :helper-text="$t('settings.new_admin_password_help')"
                      :disabled="
                        loading.resetAdminPassword || loading.configureModule
                      "
                      :invalid-message="error.admin_password"
                      ref="new_admin_password"
                    />
                    <NsTextInput
                      :label="$t('settings.confirm_admin_password')"
                      v-model="adminPasswordConfirmation"
                      type="password"
                      :password-show-label="$t('settings.show_password')"
                      :password-hide-label="$t('settings.hide_password')"
                      :disabled="
                        loading.resetAdminPassword || loading.configureModule
                      "
                      :invalid-message="error.admin_password_confirmation"
                      ref="admin_password_confirmation"
                    />
                    <NsCheckbox
                      v-model="resetTwoFactor"
                      :label="$t('settings.reset_2fa')"
                      :disabled="
                        loading.resetAdminPassword || loading.configureModule
                      "
                    />
                    <NsButton
                      kind="tertiary"
                      type="button"
                      :disabled="
                        loading.resetAdminPassword || loading.configureModule
                      "
                      @click="cancelAdminPasswordEdit"
                    >
                      {{ $t("common.cancel") }}
                    </NsButton>
                  </div>
                </template>
              </cv-accordion-item>
            </cv-accordion>
            <cv-row v-if="error.configureModule">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.configure-module')"
                  :description="error.configureModule"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule || loading.resetAdminPassword"
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                loading.resetAdminPassword
              "
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
          <cv-modal
            :visible="confirmAdminSecurityChangesVisible"
            @modal-hidden="cancelAdminSecurityConfirmation"
            @primary-click="confirmAdminSecurityChanges"
            @secondary-click="cancelAdminSecurityConfirmation"
          >
            <template slot="label">{{
              $t("settings.admin_security_confirmation_label")
            }}</template>
            <template slot="title">{{
              $t("settings.admin_security_confirmation_title")
            }}</template>
            <template slot="content">
              <p>
                {{
                  $t(
                    resetTwoFactor
                      ? "settings.confirm_admin_password_reset_2fa"
                      : "settings.confirm_admin_password_reset"
                  )
                }}
              </p>
            </template>
            <template slot="secondary-button">{{
              $t("common.cancel")
            }}</template>
            <template slot="primary-button">{{
              $t(
                resetTwoFactor
                  ? "settings.confirm_admin_password_reset_2fa_action"
                  : "settings.confirm_admin_password_reset_action"
              )
            }}</template>
          </cv-modal>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";

export default {
  name: "Settings",
  mixins: [
    TaskService,
    IconService,
    UtilService,
    QueryParamService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("settings.title") + " - " + this.appName;
  },
  data() {
    return {
      q: {
        page: "settings",
      },
      urlCheckInterval: null,
      fqdn: "",
      letsEncrypt: false,
      sshPort: "2222",
      adminPassword: "",
      adminPasswordConfirmation: "",
      adminPasswordInitialized: false,
      editingAdminPassword: false,
      resetTwoFactor: false,
      confirmAdminSecurityChangesVisible: false,
      pendingAdminPasswordReset: false,
      resetPasswordSuccess: false,
      resetPasswordSuccessTwoFactor: false,
      loading: {
        getConfiguration: false,
        configureModule: false,
        resetAdminPassword: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        fqdn: "",
        ssh_port: "",
        admin_password: "",
        admin_password_confirmation: "",
        resetAdminPassword: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    bbsUrl() {
      return this.fqdn ? "https://" + this.fqdn : "";
    },
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.watchQueryData(vm);
      vm.urlCheckInterval = vm.initUrlBindingForApp(vm, vm.q.page);
    });
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.urlCheckInterval);
    next();
  },
  created() {
    this.getConfiguration();
  },
  methods: {
    async getConfiguration() {
      this.loading.getConfiguration = true;
      this.error.getConfiguration = "";
      const taskAction = "get-configuration";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getConfigurationAborted
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.getConfigurationCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          extra: {
            title: this.$t("action." + taskAction),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`);
        this.error.getConfiguration = this.getErrorMessage(err);
        this.loading.getConfiguration = false;
        return;
      }
    },
    getConfigurationAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getConfiguration = this.$t("error.generic_error");
      this.loading.getConfiguration = false;
    },
    getConfigurationCompleted(taskContext, taskResult) {
      this.loading.getConfiguration = false;
      const config = taskResult.output;

      this.fqdn = config.fqdn || "";
      this.letsEncrypt = config.lets_encrypt;
      this.sshPort = String(config.ssh_port || 2222);
      this.adminPasswordInitialized = config.admin_password_initialized === true;
      if (!this.editingAdminPassword) {
        this.adminPassword = "";
      }
      this.focusElement("fqdn");
    },
    validateConfigureModule() {
      this.clearErrors(this);
      let isValidationOk = true;

      const fqdnPattern = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))+$/i;
      if (!fqdnPattern.test(this.fqdn.trim())) {
        this.error.fqdn = this.$t("settings.invalid_fqdn");
        this.focusElement("fqdn");
        isValidationOk = false;
      }

      const port = Number(this.sshPort);
      if (!Number.isInteger(port) || port < 1024 || port > 65535) {
        this.error.ssh_port = this.$t("settings.invalid_ssh_port");
        if (isValidationOk) {
          this.focusElement("ssh_port");
        }
        isValidationOk = false;
      }

      if (
        !this.adminPasswordInitialized &&
        this.adminPassword &&
        (this.adminPassword.length < 8 ||
          this.adminPassword.length > 128 ||
          /[\r\n]/.test(this.adminPassword) ||
          this.adminPassword.includes("\0"))
      ) {
        this.error.admin_password = this.$t("settings.invalid_admin_password");
        if (isValidationOk) {
          this.focusElement("admin_password");
        }
        isValidationOk = false;
      }
      return isValidationOk;
    },
    adminPasswordResetRequested() {
      return (
        this.adminPasswordInitialized &&
        this.editingAdminPassword &&
        (this.adminPassword !== "" ||
          this.adminPasswordConfirmation !== "" ||
          this.resetTwoFactor)
      );
    },
    saveSettings() {
      this.resetPasswordSuccess = false;
      if (!this.validateConfigureModule()) {
        return;
      }

      if (this.adminPasswordResetRequested()) {
        if (!this.validateResetAdminPassword()) {
          return;
        }
        this.confirmAdminSecurityChangesVisible = true;
        return;
      }

      this.pendingAdminPasswordReset = false;
      this.configureModule();
    },
    confirmAdminSecurityChanges() {
      if (
        this.pendingAdminPasswordReset ||
        this.loading.configureModule ||
        this.loading.resetAdminPassword
      ) {
        return;
      }

      if (
        !this.validateConfigureModule() ||
        !this.adminPasswordResetRequested() ||
        !this.validateResetAdminPassword()
      ) {
        this.confirmAdminSecurityChangesVisible = false;
        return;
      }

      this.confirmAdminSecurityChangesVisible = false;
      this.pendingAdminPasswordReset = true;
      this.configureModule();
    },
    cancelAdminSecurityConfirmation() {
      this.confirmAdminSecurityChangesVisible = false;
    },
    beginAdminPasswordEdit() {
      this.adminPassword = "";
      this.adminPasswordConfirmation = "";
      this.resetTwoFactor = false;
      this.error.admin_password = "";
      this.error.admin_password_confirmation = "";
      this.error.resetAdminPassword = "";
      this.resetPasswordSuccess = false;
      this.editingAdminPassword = true;
    },
    cancelAdminPasswordEdit() {
      this.adminPassword = "";
      this.adminPasswordConfirmation = "";
      this.resetTwoFactor = false;
      this.error.admin_password = "";
      this.error.admin_password_confirmation = "";
      this.error.resetAdminPassword = "";
      this.editingAdminPassword = false;
    },
    validateResetAdminPassword() {
      this.error.admin_password = "";
      this.error.admin_password_confirmation = "";
      if (!this.adminPassword && !this.adminPasswordConfirmation) {
        if (this.resetTwoFactor) {
          this.error.admin_password = this.$t(
            "settings.password_required_for_2fa_reset"
          );
          this.focusElement("new_admin_password");
          return false;
        }
        return true;
      }

      const passwordLength = new TextEncoder().encode(this.adminPassword).length;
      if (
        passwordLength < 8 ||
        passwordLength > 72 ||
        /[\r\n]/.test(this.adminPassword) ||
        this.adminPassword.includes("\0")
      ) {
        this.error.admin_password = this.$t(
          "settings.invalid_reset_admin_password"
        );
        this.focusElement("new_admin_password");
        return false;
      }
      if (this.adminPassword !== this.adminPasswordConfirmation) {
        this.error.admin_password_confirmation = this.$t(
          "settings.admin_password_mismatch"
        );
        this.focusElement("admin_password_confirmation");
        return false;
      }
      return true;
    },
    async resetAdminPassword() {
      this.error.resetAdminPassword = "";
      this.resetPasswordSuccess = false;

      this.loading.resetAdminPassword = true;
      const taskAction = "reset-admin-password";
      const eventId = this.getUuid();
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.resetAdminPasswordAborted
      );
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.resetAdminPasswordValidationFailed
      );
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.resetAdminPasswordCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: {
            password: this.adminPassword,
            reset_2fa: this.resetTwoFactor,
          },
          extra: {
            title: this.$t("action." + taskAction),
            eventId,
          },
        })
      );
      if (res[0]) {
        this.error.resetAdminPassword = this.getErrorMessage(res[0]);
        this.loading.resetAdminPassword = false;
      }
    },
    resetAdminPasswordAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.resetAdminPassword = this.$t("error.generic_error");
      this.loading.resetAdminPassword = false;
    },
    resetAdminPasswordValidationFailed(validationErrors) {
      this.loading.resetAdminPassword = false;
      for (const validationError of validationErrors) {
        if (validationError.field === "password") {
          this.error.admin_password = this.$t(
            "settings.invalid_reset_admin_password"
          );
        } else {
          this.error.resetAdminPassword = this.$t("error.validation_error");
        }
      }
    },
    resetAdminPasswordCompleted() {
      this.resetPasswordSuccessTwoFactor = this.resetTwoFactor;
      this.loading.resetAdminPassword = false;
      this.adminPassword = "";
      this.adminPasswordConfirmation = "";
      this.resetTwoFactor = false;
      this.editingAdminPassword = false;
      this.resetPasswordSuccess = true;
    },
    configureModuleValidationFailed(validationErrors) {
      this.pendingAdminPasswordReset = false;
      this.loading.configureModule = false;
      let focusAlreadySet = false;

      for (const validationError of validationErrors) {
        const field = validationError.field;

        if (field !== "(root)") {
          // set i18n error message
          this.error[field] = this.$t("settings." + validationError.error);
          if (
            field === "admin_password" &&
            validationError.error === "admin_password_already_initialized"
          ) {
            this.adminPasswordInitialized = true;
            this.adminPassword = "";
          }

          if (!focusAlreadySet) {
            this.focusElement(field);
            focusAlreadySet = true;
          }
        }
      }
    },
    async configureModule() {
      const isValidationOk = this.validateConfigureModule();
      if (!isValidationOk) {
        this.pendingAdminPasswordReset = false;
        return;
      }

      this.loading.configureModule = true;
      const taskAction = "configure-module";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.configureModuleAborted
      );

      // register to task validation
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.configureModuleValidationFailed
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.configureModuleCompleted
      );

      const data = {
        fqdn: this.fqdn.trim().toLowerCase(),
        lets_encrypt: this.letsEncrypt,
        ssh_port: Number(this.sshPort),
      };
      if (!this.adminPasswordInitialized && this.adminPassword) {
        data.admin_password = this.adminPassword;
      }

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data,
          extra: {
            title: this.$t("settings.configure_instance", {
              instance: this.instanceName,
            }),
            description: this.$t("common.processing"),
            eventId,
          },
        })
      );
      const err = res[0];

      if (!err && !this.adminPasswordInitialized) {
        this.adminPassword = "";
      }

      if (err) {
        console.error(`error creating task ${taskAction}`);
        this.error.configureModule = this.getErrorMessage(err);
        this.loading.configureModule = false;
        this.pendingAdminPasswordReset = false;
        return;
      }
    },
    configureModuleAborted(...args) {
      console.error(`${args[1].action} aborted`);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
      this.pendingAdminPasswordReset = false;
      this.getConfiguration();
    },
    configureModuleCompleted() {
      const resetAdminPassword = this.pendingAdminPasswordReset;
      this.pendingAdminPasswordReset = false;
      this.loading.configureModule = false;

      // reload configuration
      this.getConfiguration();
      if (resetAdminPassword) {
        this.resetAdminPassword();
      }
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
</style>
