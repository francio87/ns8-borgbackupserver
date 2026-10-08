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
          <cv-form @submit.prevent="configureModule">
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
              :loading="loading.configureModule"
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                loading.resetAdminPassword
              "
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
          <cv-row v-if="adminPasswordInitialized">
            <cv-column>
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
              <NsButton
                v-if="!editingAdminPassword"
                kind="secondary"
                :disabled="
                  loading.getConfiguration ||
                  loading.configureModule ||
                  loading.resetAdminPassword
                "
                @click="beginAdminPasswordEdit"
              >
                {{ $t("settings.modify_admin_password") }}
              </NsButton>
              <cv-form v-else @submit.prevent="resetAdminPassword">
                <NsTextInput
                  :label="$t('settings.new_admin_password')"
                  v-model="adminPassword"
                  type="password"
                  :password-show-label="$t('settings.show_password')"
                  :password-hide-label="$t('settings.hide_password')"
                  :helper-text="$t('settings.new_admin_password_help')"
                  :disabled="loading.resetAdminPassword || loading.configureModule"
                  :invalid-message="error.admin_password"
                  ref="new_admin_password"
                />
                <NsTextInput
                  :label="$t('settings.confirm_admin_password')"
                  v-model="adminPasswordConfirmation"
                  type="password"
                  :password-show-label="$t('settings.show_password')"
                  :password-hide-label="$t('settings.hide_password')"
                  :disabled="loading.resetAdminPassword || loading.configureModule"
                  :invalid-message="error.admin_password_confirmation"
                  ref="admin_password_confirmation"
                />
                <NsCheckbox
                  v-model="resetTwoFactor"
                  :label="$t('settings.reset_2fa')"
                  :disabled="loading.resetAdminPassword || loading.configureModule"
                />
                <cv-row v-if="error.resetAdminPassword">
                  <cv-column>
                    <NsInlineNotification
                      kind="error"
                      :title="$t('action.reset-admin-password')"
                      :description="error.resetAdminPassword"
                      :showCloseButton="false"
                    />
                  </cv-column>
                </cv-row>
                <NsButton
                  kind="primary"
                  :loading="loading.resetAdminPassword"
                  :disabled="
                    loading.resetAdminPassword || loading.configureModule
                  "
                >
                  {{ $t("settings.reset_admin_password") }}
                </NsButton>
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
              </cv-form>
            </cv-column>
          </cv-row>
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
      if (!this.validateResetAdminPassword()) {
        return;
      }

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
        return;
      }
    },
    configureModuleAborted(...args) {
      console.error(`${args[1].action} aborted`);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
      this.getConfiguration();
    },
    configureModuleCompleted() {
      this.loading.configureModule = false;

      // reload configuration
      this.getConfiguration();
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
</style>
