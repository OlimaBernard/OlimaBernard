import { Component, OnInit } from '@angular/core';
import { FormGroup, FormBuilder, Validators, FormControl } from '@angular/forms';

@Component({
  selector: 'app-changepassword',
  templateUrl: './changepassword.component.html',
  styleUrls: ['./changepassword.component.sass']
})
export class ChangepasswordComponent implements OnInit {
  public showNewPassword = false;
  public showConfirmPassword = false;
  public showPasswordRequirementsPopup = false; // Added variable
  public changePasswordForm: FormGroup;
  public passwordStrength: string = '';
  public passwordStrengthText: string = '';
  public passwordStrengthColor: string = '';

  constructor(private formBuilder: FormBuilder) {
    this.changePasswordForm = this.formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      newPassword: ['', [Validators.required, this.passwordStrengthValidator()]],
      confirmPassword: ['', Validators.required]
    }, {
      validator: this.passwordMatchValidator
    });
  }

  ngOnInit(): void {
  }

  togglePassword(field: string) {
    switch (field) {
      case 'current':
      case 'new':
        this.showNewPassword = !this.showNewPassword;
        if (this.showNewPassword) {
          this.showPasswordRequirementsPopup = true; // Show requirements popup when new password field is clicked
        }
        break;
      case 'confirm':
        this.showConfirmPassword = !this.showConfirmPassword;
        break;
      default:
        break;
    }
  }

  passwordMatchValidator(formGroup: FormGroup) {
    const newPassword = formGroup.get('newPassword')?.value;
    const confirmPassword = formGroup.get('confirmPassword')?.value;

    if (newPassword !== confirmPassword) {
      formGroup.get('confirmPassword')?.setErrors({ passwordMismatch: true });
    } else {
      formGroup.get('confirmPassword')?.setErrors(null);
    }
  }

  onSubmit() {
    // Submit logic here
  }

  passwordStrengthValidator() {
    const spaceRegex = /\s/; // Regex for spaces

    const spaceValidator = (control: FormControl): { [key: string]: boolean } | null => {
      const value: string = control.value;
      if (value.trim().length === 0) {
        return { 'spaces': true };
      }
      return null;
    };

    return (control) => {
      const password = control.value;
      const minLength = 8; // Minimum password length
      const uppercaseRegex = /[A-Z]/; // Regex for uppercase letters
      const lowercaseRegex = /[a-z]/; // Regex for lowercase letters
      const numberRegex = /[0-9]/; // Regex for numbers
      const specialCharRegex = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/; // Regex for special characters

      const isStrong = password.length >= minLength &&
        uppercaseRegex.test(password) &&
        lowercaseRegex.test(password) &&
        numberRegex.test(password) &&
        !spaceRegex.test(password) &&
        specialCharRegex.test(password);

      if (!isStrong) {
        return { 'weakPassword': true };
      }
      return null;
    };
  }

  updatePasswordStrength(): void {
    const newPassword = this.changePasswordForm.get('newPassword')?.value;
    this.passwordStrength = this.calculatePasswordStrength(newPassword);
    this.updatePasswordStrengthText();
  }

  calculatePasswordStrength(password: string): string {
    const minLength = 8;
    const minUppercase = 1;
    const minLowercase = 1;
    const minNumbers = 1;
    const minSpecialChars = 1;

    let score = 0;

    if (password.length >= minLength) {
      score += 1;
    }

    if (/[A-Z]/.test(password)) {
      score += 1;
    }

    if (/[a-z]/.test(password)) {
      score += 1;
    }

    if (/\d/.test(password)) {
      score += 1;
    }

    if (/[^A-Za-z0-9]/.test(password)) {
      score += 1;
    }

    if (score <= 2) {
      return 'weak';
    } else if (score <= 4) {
      return 'medium';
    } else {
      return 'strong';
    }
  }

  updatePasswordStrengthText(): void {
    switch (this.passwordStrength) {
      case 'weak':
        this.passwordStrengthText = 'Weak Password';
        this.passwordStrengthColor = 'red';
        break;
      case 'medium':
        this.passwordStrengthText = 'Good Password';
        this.passwordStrengthColor = 'orange';
        break;
      case 'strong':
        this.passwordStrengthText = 'Strong Password';
        this.passwordStrengthColor = 'green';
        break;
      default:
        this.passwordStrengthText = '';
        this.passwordStrengthColor = '';
        break;
    }
  }
}
